"""Cross-exchange trade with the price leg included, and better-motivated exits (sensitivity, not a decision).

Same trades as the Phase 1 test (top 20% of the trailing 3-day Binance–Bybit funding gap): short the perp on
the higher-funding venue, long it on the other. Phase 1 counted funding only; here P&L also includes the
change in the two perps' prices. Exits (fixed before running; all capped at 30 days):
  fixed_7d       exit after 21 windows (the original test)
  gap_closes     first window where the funding gap in the trade's favour is under 0.1 bp
  price_converges first close where the shorted perp is no longer priced above the bought one

Run:  python research/cross_venue_pnl.py   (writes reports/cross_venue/report.md)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from funding.dataset import core_end
from funding.panels import monthly_universe, prices_8h, to_8h
from funding.sources import tradfi_coins
from funding.store import Store

OUT = Path("reports/cross_venue/report.md")
COST = 2 * (0.0005 + 0.00055)  # four taker legs, Binance + Bybit
MAX_HOLD = 90  # windows (30 days)
SIGNAL_WINDOW = 9


def member_mask(universe, index, coins):
    month = (index - pd.Timedelta(minutes=1)).tz_localize(None).to_period("M")
    mask = pd.DataFrame(False, index=index, columns=coins)
    for m, cs in universe.groupby(universe["month"].dt.tz_localize(None).dt.to_period("M"))["coin"]:
        mask.loc[month == m, mask.columns.intersection(cs)] = True
    return mask


def trades_for_coin(gap, spread, px_bn, px_bb, signal, entries) -> list[dict]:
    """gap = Bybit − Binance funding per window; spread = Bybit / Binance perp price − 1 at each close."""
    rows = []
    n = len(gap)
    for i in entries:
        d = np.sign(signal[i])  # +1: short Bybit, long Binance
        if d == 0 or not (np.isfinite(px_bn[i]) and np.isfinite(px_bb[i])):
            continue
        last = min(i + MAX_HOLD, n - 1)
        exits = {"fixed_7d": min(i + 21, last)}
        favour = d * gap[i + 1:last + 1]
        closed = np.flatnonzero(np.nan_to_num(favour, nan=0.0) < 1e-5)
        exits["gap_closes"] = i + 1 + closed[0] if len(closed) else last
        conv = np.flatnonzero(np.nan_to_num(d * spread[i + 1:last + 1], nan=1.0) <= 0)
        exits["price_converges"] = i + 1 + conv[0] if len(conv) else last
        for name, j in exits.items():
            if not (np.isfinite(px_bn[j]) and np.isfinite(px_bb[j])):
                continue
            fund = d * np.nansum(gap[i + 1:j + 1])
            r_bn, r_bb = px_bn[j] / px_bn[i] - 1, px_bb[j] / px_bb[i] - 1
            price = -d * (r_bb - r_bn)  # short the d-side, long the other
            rows.append({"i": i, "exit": name, "days": (j - i) / 3, "funding_bp": fund * 1e4, "price_bp": price * 1e4,
                         "entry_spread_bp": d * spread[i] * 1e4})
    return rows


def main():
    store = Store()
    universe = monthly_universe(store.read("daily"), tradfi_coins())
    raw = store.read("funding")
    f = to_8h(raw[raw["venue"].isin(["binance", "bybit"])]).loc["2021-01-01":]
    f = f.loc[:core_end(f)]
    px = prices_8h(store.read("perp8h"))
    coins = f["binance"].columns
    gap_all = f["bybit"].reindex(columns=coins) - f["binance"]
    member = member_mask(universe, f.index, coins)
    signal_all = gap_all.rolling(SIGNAL_WINDOW, min_periods=SIGNAL_WINDOW).mean().where(member)
    threshold = signal_all.abs().stack().dropna().quantile(0.8)  # top 20% of signals, pooled (as in Phase 1)

    rows = []
    for c in coins:
        if ("binance", c) not in px or ("bybit", c) not in px:
            continue
        bn = px[("binance", c)].reindex(f.index).to_numpy()
        bb = px[("bybit", c)].reindex(f.index).to_numpy()
        sig = signal_all[c].to_numpy()
        entries = np.flatnonzero(np.abs(np.nan_to_num(sig)) >= threshold)
        for r in trades_for_coin(gap_all[c].to_numpy(), bb / bn - 1, bn, bb, sig, entries):
            r.update(coin=c, ts=f.index[r["i"]])
            rows.append(r)
    t = pd.DataFrame(rows)
    t["total_bp"] = t["funding_bp"] + t["price_bp"]
    t["net_bp"] = t["total_bp"] - COST * 1e4
    t["year"] = t["ts"].dt.year

    out = ["# Cross-exchange trade: funding plus price, and alternative exits\n\n"
           "Sensitivity analysis (not a decision). Same trades as the Phase 1 test: the top 20% of the trailing "
           "3-day Binance–Bybit funding gap; short the perp on the higher-funding venue, long the other. Phase 1 "
           "counted funding only; here the change in the two perps' prices is included. All exits capped at 30 "
           f"days. Round-trip cost {COST * 1e4:.0f} bp. Prices are 8-hour closes on both venues at the same "
           "timestamps.\n"]

    def section(title, df, note=""):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=".2f") + "\n")

    g = t.groupby("exit")
    summary = pd.DataFrame({
        "trades": g.size(), "avg hold (days)": g["days"].mean(),
        "funding bp": g["funding_bp"].mean(), "price bp": g["price_bp"].mean(), "total bp": g["total_bp"].mean(),
        "net of cost bp": g["net_bp"].mean(), "median net bp": g["net_bp"].median(),
        "share net > 0": g["net_bp"].apply(lambda s: (s > 0).mean()),
    }).loc[["fixed_7d", "gap_closes", "price_converges"]]
    section("1. Average trade by exit rule (2021–2026)", summary)
    by_year = t.pivot_table(index="year", columns="exit", values="net_bp", aggfunc="mean")[
        ["fixed_7d", "gap_closes", "price_converges"]]
    section("2. Net P&L per trade by year (bp, after costs)", by_year)
    first = t[t["exit"] == "fixed_7d"]
    section("3. Was the high-funding perp also the expensive one at entry?", pd.DataFrame({
        "median entry price gap, shorted vs bought perp (bp)": [first["entry_spread_bp"].median()],
        "share of trades where the shorted perp was richer": [(first["entry_spread_bp"] > 0).mean()],
    }), "Positive: the trade shorts the richer perp, so convergence adds to the funding.")
    big = t.assign(major=t["coin"].isin(["BTC", "ETH"])).groupby(["exit", "major"])["price_bp"].mean().unstack()
    section("4. Price leg: BTC/ETH vs other coins (bp, mean)", big.rename(columns={True: "BTC/ETH", False: "others"}))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
