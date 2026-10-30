"""Extension A: does the no-arbitrage band widen with frictions? Spec: docs/plan.md, "Extension A spec".

Compares Binance–Hyperliquid and Binance–dYdX funding gaps with Binance–Bybit on matched coin-windows.
Run after research/build_extensions.py hyperliquid / dydx:  python research/extension_a_onchain.py
Writes reports/extension_a/report.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from funding.dataset import core_end
from funding.panels import monthly_universe, to_8h
from funding.sources import tradfi_coins
from funding.store import Store

OUT = Path("reports/extension_a/report.md")
START = "2023-11-01"
YEARS = (2024, 2025, 2026)
FEE = {"binance": 0.0005, "bybit": 0.00055, "hyperliquid": 0.00045, "dydx": 0.0005}  # base-tier taker, per leg
PER_YEAR = 3 * 365


def round_trip(a: str, b: str) -> float:
    return 2 * (FEE[a] + FEE[b])


def member_mask(universe: pd.DataFrame, index: pd.DatetimeIndex, coins) -> pd.DataFrame:
    month = (index - pd.Timedelta(minutes=1)).tz_localize(None).to_period("M")
    mask = pd.DataFrame(False, index=index, columns=coins)
    for m, cs in universe.groupby(universe["month"].dt.tz_localize(None).dt.to_period("M"))["coin"]:
        mask.loc[month == m, mask.columns.intersection(cs)] = True
    return mask


def half_life_hours(gap: pd.DataFrame) -> float:
    df = pd.DataFrame({"y": gap.stack(), "x": gap.shift(1).stack()}).dropna()
    phi = np.polyfit(df["x"], df["y"], 1)[0]
    return np.log(0.5) / np.log(phi) * 8 if 0 < phi < 1 else np.nan


def stats(gap: pd.DataFrame, a: pd.DataFrame, b: pd.DataFrame, cost: float) -> dict:
    g = gap.stack().dropna()
    # Phase 1 trade: enter on the trailing 3-day gap, collect the gap over the next 7 days.
    signal = gap.rolling(9, min_periods=9).mean()
    fwd = gap[::-1].rolling(21, min_periods=1).sum()[::-1].shift(-1)
    obs = pd.DataFrame({"s": signal.stack(), "c": (np.sign(signal) * fwd).stack()}).dropna()
    top = obs[obs["s"].abs() >= obs["s"].abs().quantile(0.8)]["c"] if len(obs) else pd.Series(dtype=float)
    return {"coin-windows": len(g), "median |gap| bp/8h": g.abs().median() * 1e4,
            "90th pct |gap| bp/8h": g.abs().quantile(0.9) * 1e4,
            "half-life (hours)": half_life_hours(gap),
            "venue correlation": pd.concat([a.stack(), b.stack()], axis=1).dropna().corr().iloc[0, 1],
            "top-quintile 7d gap bp": top.mean() * 1e4, "round trip bp": cost * 1e4,
            "share of top quintile beating cost": (top > cost).mean() if len(top) else np.nan}


def main():
    store = Store()
    universe = monthly_universe(store.read("daily"), tradfi_coins())
    raw = store.read("funding")
    f = to_8h(raw[raw["venue"].isin(FEE)]).loc[START:]
    f = f.loc[:core_end(f)]
    coins = f["binance"].columns
    member = member_mask(universe, f.index, coins)
    venue = {v: f[v].reindex(columns=coins) for v in FEE}

    out = ["# Extension A: does the no-arbitrage band widen with frictions?\n\n"
           f"Funding gaps between Binance and two on-chain venues (Hyperliquid, dYdX) vs the Binance–Bybit "
           f"baseline on **matched** coin-windows, {START[:7]} to {f.index[-1]:%Y-%m}. Hourly funding summed into "
           "8-hour windows. Spec: [docs/plan.md](../../docs/plan.md).\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=fmt) + "\n")

    levels = {}
    for v, p in venue.items():
        x = p.where(member).stack().dropna()
        levels[v] = {"coins": p.where(member).notna().any().sum(),
                     "median funding % a year": x.median() * PER_YEAR * 100,
                     "share at 0.01% floor": ((x - 1e-4).abs() < 1e-7).mean(), "share negative": (x < 0).mean()}
    section("0. Funding by venue (universe coins)", pd.DataFrame(levels).T,
            "Different floors mean part of any gap is mechanical rather than an arbitrage opportunity.")

    verdicts, tables = {}, {}
    for other in ("hyperliquid", "dydx"):
        both = member & venue["binance"].notna() & venue["bybit"].notna() & venue[other].notna()
        pair_gap = (venue[other] - venue["binance"]).where(both)
        base_gap = (venue["bybit"] - venue["binance"]).where(both)
        rows = {}
        for label, gap, b, cost in [(f"Binance–{other.capitalize()}", pair_gap, other, round_trip("binance", other)),
                                    ("Binance–Bybit (matched)", base_gap, "bybit", round_trip("binance", "bybit"))]:
            for yr in ("all", *YEARS):
                sl = slice(None) if yr == "all" else str(yr)
                rows[(label, yr)] = stats(gap.loc[sl], venue["binance"].where(both).loc[sl],
                                          venue[b].where(both).loc[sl], cost)
        t = pd.DataFrame(rows).T
        tables[other] = t
        section(f"1{'ab'[other == 'dydx']}. Binance–{other.capitalize()} vs Binance–Bybit, matched", t)
        pair, base = f"Binance–{other.capitalize()}", "Binance–Bybit (matched)"
        wins = sum(t.loc[(pair, y), "median |gap| bp/8h"] > t.loc[(base, y), "median |gap| bp/8h"]
                   and t.loc[(pair, y), "half-life (hours)"] > t.loc[(base, y), "half-life (hours)"] for y in YEARS)
        verdicts[other] = wins

    # Robustness (added after seeing results; not part of the decision): dYdX has no 0.01% floor, so remove
    # Binance's floor before differencing to separate the formula difference from genuine gaps.
    both = member & venue["binance"].notna() & venue["bybit"].notna() & venue["dydx"].notna()
    adj = (venue["dydx"] - (venue["binance"] - 1e-4)).where(both)
    base = (venue["bybit"] - venue["binance"]).where(both)
    rob = pd.DataFrame({
        (label, yr): stats(g.loc[slice(None) if yr == "all" else str(yr)],
                           venue["binance"].where(both).loc[slice(None) if yr == "all" else str(yr)],
                           venue[b].where(both).loc[slice(None) if yr == "all" else str(yr)], cost)
        for label, g, b, cost in [("Binance–Dydx, floor-adjusted", adj, "dydx", round_trip("binance", "dydx")),
                                  ("Binance–Bybit (matched)", base, "bybit", round_trip("binance", "bybit"))]
        for yr in ("all", *YEARS)}).T[["median |gap| bp/8h", "90th pct |gap| bp/8h", "half-life (hours)",
                                       "top-quintile 7d gap bp", "share of top quintile beating cost"]]
    section("1c. Robustness (added after results): dYdX with Binance's 0.01% floor removed", rob,
            "dYdX's funding has no interest floor (median 0.00% vs 10.95% a year elsewhere), so the raw gap partly "
            "reflects the formula, not frictions. Not part of the pre-registered decision.")

    holds = all(w >= 2 for w in verdicts.values())
    out.append("\n## 2. Pre-registered prediction\n\n"
               + "".join(f"- Binance–{o.capitalize()}: wider median gap **and** longer half-life than matched "
                         f"Binance–Bybit in **{w} of {len(YEARS)}** years (need 2).\n" for o, w in verdicts.items())
               + f"- **Prediction {'HOLDS' if holds else 'DOES NOT HOLD'}** (both pairs must pass).\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
