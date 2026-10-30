"""Phase 4: daily MILP allocator vs the Phase 3 benchmark. Spec: docs/plan.md, "Phase 4 spec".

Run after research/build_data.py:  python research/phase4_allocator.py   (writes reports/phase4/report.md)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
from phase3_backtest import BASELINE, COSTS, NAV, START, STRATEGIES, YEARS, attribution, backtest, daily_excess, summary

from funding import metrics
from funding.backtest import run, run_joint
from funding.dataset import VENUES, investable_rows, load, tbill_8h
from funding.forecast import walk_forward
from funding.milp import MAJORS, Params, make_allocator

OUT = Path("reports/phase4/report.md")
CROSS_MARGIN = lambda c: 1.10 if c in MAJORS else 1.30  # noqa: E731
PRIMARY = "P MILP"


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc7, fc30 = walk_forward(rows), walk_forward(rows, target="target_30d")

    def milp_run(fc: pd.Series, params: Params, margin=None):
        return run_joint(panels, make_allocator(fc, panels, tbill, params), NAV, tbill, COSTS, margin, START)

    ledgers = {name: backtest(panels, fc7, tbill, name) for name in STRATEGIES}  # Phase 3 trials
    cross_costs = {v: dataclasses.replace(c, margin_buffer=0.10) for v, c in COSTS.items()}  # BTC/ETH factor 1.10
    s1_cross = [run(panels[v], pd.Series(dtype=float), STRATEGIES[BASELINE][0](cross_costs[v]), 2, NAV / 2, tbill,
                    cross_costs[v], START) for v in VENUES]
    ledgers["S1 passive, cross-margin"] = sum(b[["equity_start", "pnl", "n_held", "liquidations", "funding",
                                                 "basis", "unhedged", "costs", "liquidation", "cash", "traded"]]
                                              for b in s1_cross).assign(tbill=s1_cross[0]["tbill"])
    runs = {
        PRIMARY: (fc30["M3_regression"], Params(), None),
        "R1 MILP, EWMA forecast": (fc30["M2_ewma"], Params(), None),
        "R2 MILP, cross-margin": (fc30["M3_regression"], Params(), CROSS_MARGIN),
        "A1 fixed 50/50, no transfers": (fc30["M3_regression"], Params(transfers=False), None),
        "A2 no per-coin caps": (fc30["M3_regression"], Params(per_coin_caps=False), None),
        "A3 7-day horizon": (fc7["M3_regression"], Params(horizon_days=7), None),
    }
    for name, (fc, params, margin) in runs.items():
        print(f"running {name}", flush=True)
        ledgers[name] = milp_run(fc, params, margin)

    rets = {n: daily_excess(ld) for n, ld in ledgers.items()}
    trials = [metrics.sharpe(r) for r in rets.values()]
    out = ["# Phase 4: MILP allocator\n\n"
           f"NAV ${NAV:,.0f} across Binance and Bybit, {START[:4]}-01 to "
           f"{ledgers[PRIMARY].index[-1]:%Y-%m}, same engine, costs and conservative assumptions as Phase 3. "
           "Daily HiGHS solve, executed at the next close. Spec: [docs/plan.md](../../docs/plan.md). "
           "All returns in excess of the 3-month T-bill.\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=fmt) + "\n")

    table = pd.DataFrame({n: summary(ld) for n, ld in ledgers.items()}).T
    table["deflated Sharpe"] = [metrics.deflated_sharpe(rets[n], trials) for n in table.index]
    section("1. Summary (full period)", table,
            f"Deflated Sharpe counts all {len(trials)} runs (Phase 3's six, S1 under cross-margin, and Phase 4's six).")
    by_year = pd.DataFrame({n: r.groupby(r.index.year).sum() * 100 for n, r in rets.items()}).T
    section("2. Excess return by year (%)", by_year, "2026 is a partial year.")
    section("3. P&L attribution (% of NAV a year)",
            pd.DataFrame({n: attribution(ld) for n, ld in ledgers.items()}).T)

    stress = {}
    for n, ld in ledgers.items():
        r = rets[n]
        stress[n] = {"worst 30 days %": r.rolling(30).sum().min() * 100,
                     "liquidations": int(ld["liquidations"].sum()),
                     "max share of NAV on one venue %": ld["max_venue_share"].max() * 100
                     if "max_venue_share" in ld else 50.0}
    section("4. Stress", pd.DataFrame(stress).T,
            "Max share on one venue = the loss if that exchange had failed at the worst moment. Phase 3 "
            "strategies keep a fixed 50/50 split.")

    diff, (lo, hi), p = metrics.paired_sharpe_test(rets[PRIMARY], rets[BASELINE])
    positive = int((by_year.loc[PRIMARY, list(YEARS)] > 0).sum())
    adds = p < 0.10 and positive >= 3
    d2, _, p2 = metrics.paired_sharpe_test(rets["R2 MILP, cross-margin"], rets["S1 passive, cross-margin"])
    out.append(
        f"\n## 5. Decision (rule fixed in advance)\n\n"
        f"- Sharpe difference {PRIMARY} − {BASELINE}: **{diff:+.2f}** (95% interval {lo:+.2f} to {hi:+.2f}); "
        f"P(difference ≤ 0) = **{p:.2f}** (need < 0.10).\n"
        f"- {PRIMARY} positive in **{positive} of {len(YEARS)}** years (need 3).\n"
        f"- **The MILP adds value: {'YES' if adds else 'NO'}.**\n"
        f"- Deflated Sharpe of {PRIMARY} over {len(trials)} trials: **{table.at[PRIMARY, 'deflated Sharpe']:.0%}**.\n"
        f"- Like-for-like under cross-margin (not part of the decision): R2 − S1 cross-margin Sharpe "
        f"{d2:+.2f}, P(difference ≤ 0) = {p2:.2f}.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
