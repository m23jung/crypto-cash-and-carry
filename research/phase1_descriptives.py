"""Phase 1: descriptive statistics and the cross-venue go/no-go test.

Run after research/build_data.py:  python research/phase1_descriptives.py
Writes reports/phase1/report.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from funding.dataset import core_end
from funding.panels import UNIVERSE_SIZE, monthly_universe, to_8h
from funding.sources import fred, tradfi_coins
from funding.store import Store

PER_YEAR = 3 * 365  # 8-hour periods per year
FLOOR = 0.0001  # 0.01% per 8h: funding when the premium sits inside the clamp
MAJORS = ["BTC", "ETH"]
# Base-tier fees per leg, fraction of notional (taker, maker); checked 2026-10-28 (see README decisions log).
# ponytail: one static schedule for 2021-2026; Binance's VIP0 perp taker was 0.04% in earlier years.
FEES = {"binance": (0.0005, 0.0002), "bybit": (0.00055, 0.0002)}
ROUND_TRIP = {k: 2 * sum(FEES[v][i] for v in FEES) for i, k in enumerate(["taker", "maker"])}  # 4 legs
SIGNAL_WINDOW = 9  # trailing 3 days of 8h periods
HORIZONS = {"3d": 9, "7d": 21, "30d": 90}
DECIDING_HORIZON = "7d"
OUT = Path("reports/phase1/report.md")


def load():
    store = Store()
    universe = monthly_universe(store.read("daily"), tradfi_coins())
    raw = store.read("funding")
    f = to_8h(raw).loc["2021-01-01":]
    f = f.loc[:core_end(f)]
    payments = to_8h(raw, "count").reindex(f.index)
    # A window ending at 00:00 on the 1st belongs to the previous month.
    month = (f.index - pd.Timedelta(minutes=1)).tz_localize(None).to_period("M")
    member = pd.DataFrame(False, index=f.index, columns=f["binance"].columns)
    for m, coins in universe.groupby(universe["month"].dt.tz_localize(None).dt.to_period("M"))["coin"]:
        member.loc[month == m, member.columns.intersection(coins)] = True
    bn, bb = f["binance"], f["bybit"].reindex(columns=f["binance"].columns)
    tbill = (fred("DGS3MO") / 100 / PER_YEAR).tz_localize("UTC")
    tbill = tbill.reindex(tbill.index.union(f.index)).ffill().shift(1).reindex(f.index)  # yesterday's print
    return bn, bb, member, tbill, universe, payments


def by_year(x: pd.Series | pd.DataFrame):
    return x.groupby(x.index.get_level_values(0).year)  # works for (time) and (time, coin) indexes


def pooled(panel: pd.DataFrame) -> pd.Series:
    return panel.stack()


def ar1(panel: pd.DataFrame) -> tuple[float, float]:
    """Pooled AR(1) slope of a per-8h series across coins, and its half-life in days."""
    df = pd.DataFrame({"y": panel.stack(), "x": panel.shift(1).stack()}).dropna()
    phi = np.polyfit(df["x"], df["y"], 1)[0]
    return phi, np.log(0.5) / np.log(phi) / 3 if 0 < phi < 1 else np.nan


def go_no_go(gap: pd.DataFrame, member: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Collected gap over each horizon after entering in the direction of the trailing 3-day gap.

    Entry needs universe membership and a full trailing window; after entry the position is held
    even if the coin drops out (a delisting just stops the payments).
    """
    signal = gap.rolling(SIGNAL_WINDOW, min_periods=SIGNAL_WINDOW).mean().where(member)
    rows = {"abs_signal_bp": pooled(signal.abs()) * 1e4}
    for name, n in HORIZONS.items():
        fwd = gap[::-1].rolling(n, min_periods=1).sum()[::-1].shift(-1)  # sum of g over t+1..t+n
        rows[name] = pooled((np.sign(signal) * fwd).where(signal.notna())) * 1e4
    obs = pd.DataFrame(rows).dropna()
    obs["quintile"] = pd.qcut(obs["abs_signal_bp"], 5, labels=[1, 2, 3, 4, 5])
    table = obs.groupby("quintile", observed=True)[["abs_signal_bp", *HORIZONS]].mean()
    table["share_7d_>_taker_cost"] = obs.groupby("quintile", observed=True)[DECIDING_HORIZON].apply(
        lambda s: (s > ROUND_TRIP["taker"] * 1e4).mean())
    top = obs[obs["quintile"] == 5]
    years = top.groupby(top.index.get_level_values(0).year)[DECIDING_HORIZON].agg(["mean", "count"])
    years["beats_taker_cost"] = years["mean"] > ROUND_TRIP["taker"] * 1e4
    full = table.loc[5, DECIDING_HORIZON] > ROUND_TRIP["taker"] * 1e4
    return table, years, bool(full and years["beats_taker_cost"].sum() >= 4)


def main():
    bn, bb, member, tbill, universe, payments = load()
    both = member & bn.notna() & bb.notna()
    bn_u, bb_u = bn.where(both), bb.where(both)
    gap = bb - bn
    out = [f"# Phase 1: funding descriptives and go/no-go\n\n"
           f"Binance and Bybit USDT perps, {bn.index[0]:%Y-%m-%d} to {bn.index[-1]:%Y-%m-%d}, funding summed "
           f"into 8-hour windows. Universe: monthly top {UNIVERSE_SIZE} by trailing Binance volume among coins "
           f"on both venues, {universe['coin'].nunique()} distinct coins including later-delisted ones. "
           f"{int(both.sum().sum()):,} coin-periods with both venues.\n"]

    def section(title, df, note="", fmt="{:.2f}"):
        out.append(f"\n## {title}\n\n{note}\n\n" if note else f"\n## {title}\n\n")
        out.append(df.to_markdown(floatfmt=fmt.strip("{}:")) + "\n")

    coverage = {}
    for v, p in [("binance", bn), ("bybit", bb)]:
        missing = p.isna() & member
        coverage[f"{v} % windows missing"] = by_year(missing.stack()).sum() / by_year(member.stack()).sum() * 100
        n = payments[v].reindex(columns=member.columns).where(member)
        paid = by_year(n.notna().stack()).sum()
        for k, label in [(1, "8h"), (2, "4h"), (8, "1h")]:
            coverage[f"{v} % paid every {label}"] = by_year((n == k).stack()).sum() / paid * 100
    cov = pd.DataFrame(coverage)
    cov.insert(0, "member coin-windows", by_year(member.stack()).sum())
    section("0. Data coverage", cov,
            "Within the universe: share of 8-hour windows with no funding payment recorded, and how often "
            "each venue settled funding (payments per 8-hour window).", fmt="{:.1f}")
    worst_cov = (bb.isna() & member).sum().div(member.sum()).where(member.sum() > 0).nlargest(5).mul(100).round(1)
    out.append("\nCoins with the most missing Bybit windows while in the universe (%):\n\n"
               + worst_cov.rename("% missing").to_frame().to_markdown() + "\n")

    ann = lambda x: x * PER_YEAR * 100  # noqa: E731  per-8h fraction -> % a year
    level = pd.DataFrame({
        "BTC binance": by_year(bn_u.get("BTC")).mean().pipe(ann),
        "ETH binance": by_year(bn_u.get("ETH")).mean().pipe(ann),
        "universe binance": by_year(bn_u.mean(axis=1)).mean().pipe(ann),
        "universe binance median coin": by_year(pooled(bn_u)).median().pipe(ann),
        "universe bybit": by_year(bb_u.mean(axis=1)).mean().pipe(ann),
        "T-bill": by_year(tbill).mean().pipe(ann),
    })
    level["universe excess over T-bill"] = level["universe binance"] - level["T-bill"]
    section("1. Funding level vs cash (% a year)", level,
            "Average funding a short perp position receives, annualised; universe is equal-weighted. The median "
            "coin column is the median 8-hour print, annualised, which is robust to squeeze-driven tails.")

    def share(cond, panel):
        return by_year(cond.where(panel.notna()).stack()).mean() * 100

    floor_tbl = pd.DataFrame({
        f"{v} {grp}": share((p[cols] - FLOOR).abs() < 1e-7, p[cols])
        for v, p in [("binance", bn_u), ("bybit", bb_u)]
        for grp, cols in [("BTC+ETH", MAJORS), ("others", [c for c in p.columns if c not in MAJORS])]
    })
    section("2. Share of periods exactly at the 0.01% floor (%)", floor_tbl)

    neg = pd.DataFrame({
        "binance % negative": share(bn_u < 0, bn_u), "bybit % negative": share(bb_u < 0, bb_u),
        "binance 1st pct (bp/8h)": by_year(pooled(bn_u)).quantile(0.01) * 1e4,
        "binance 99th pct (bp/8h)": by_year(pooled(bn_u)).quantile(0.99) * 1e4,
    })
    section("3. Negative funding and tails", neg)
    worst = pooled(bn_u).nsmallest(5).mul(1e4).round(1).rename("bp per 8h")
    out.append("\nWorst Binance prints (bp per 8h):\n\n" + worst.to_frame().to_markdown() + "\n")

    persistence = pd.DataFrame(
        [ar1(bn_u), ar1(bb_u), ar1(gap.where(both))],
        index=["binance funding", "bybit funding", "cross-venue gap (bybit-binance)"],
        columns=["AR(1) per 8h", "half-life (days)"],
    )
    section("4. Persistence (pooled AR(1))", persistence, fmt="{:.3f}")

    g = gap.where(both)
    gap_tbl = pd.DataFrame({
        "mean |gap| bp/8h": by_year(pooled(g.abs())).mean() * 1e4,
        "median |gap| bp/8h": by_year(pooled(g.abs())).median() * 1e4,
        "90th pct |gap| bp/8h": by_year(pooled(g.abs())).quantile(0.9) * 1e4,
        "mean |gap| % a year": by_year(pooled(g.abs())).mean() * PER_YEAR * 100,
        "BTC+ETH mean |gap| bp/8h": by_year(pooled(g[MAJORS].abs())).mean() * 1e4,
        "venue correlation": [pd.concat([pooled(bn_u.loc[str(y)]), pooled(bb_u.loc[str(y)])], axis=1).corr().iloc[0, 1]
                              for y in sorted(set(g.index.year))],
    })
    section("5. Cross-venue funding gap", gap_tbl,
            f"Round-trip cost of a perp-perp pair (4 legs): taker {ROUND_TRIP['taker'] * 1e4:.0f} bp, "
            f"maker {ROUND_TRIP['maker'] * 1e4:.0f} bp.")

    table, years, go = go_no_go(gap, both)
    section("6. Go/no-go: gap collected after entering on the trailing 3-day gap (bp)", table,
            "Rows are quintiles of |trailing gap|. Columns 3d/7d/30d are the gap collected over that horizon "
            "in the signal's direction, before costs.")
    out.append("\nTop quintile, collected 7-day gap by year (bp):\n\n" + years.to_markdown(floatfmt=".1f") + "\n")
    out.append(f"\n**Decision (rule fixed before the data): {'GO' if go else 'NO-GO'}.** Top-quintile 7-day gap "
               f"{table.loc[5, DECIDING_HORIZON]:.1f} bp vs taker cost {ROUND_TRIP['taker'] * 1e4:.0f} bp; "
               f"beats it in {int(years['beats_taker_cost'].sum())} of {len(years)} years (need 4).\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
