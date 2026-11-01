"""Phase 4: daily single-venue MILP allocator vs the Phase 3 benchmark. Spec: docs/plan.md, "Phase 4 spec".

Each venue is its own $500k book, as in Phase 3. The first version allocated jointly across venues with
capital transfers; it added nothing (fixed 50/50 split: 0.60% vs 0.67% a year) and was replaced. Its runs
still count as trials (EARLIER_TRIALS).

Run after research/build_data.py:  python research/phase4_allocator.py   (writes reports/phase4/report.md)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
from phase3_backtest import (
    BASELINE,
    COMPONENTS,
    COSTS,
    NAV,
    START,
    STRATEGIES,
    YEARS,
    attribution,
    backtest,
    daily_excess,
    summary,
)

from funding import metrics
from funding.backtest import run, run_daily
from funding.dataset import VENUES, investable_rows, load, tbill_8h
from funding.forecast import walk_forward
from funding.milp import MAJORS, Params, make_allocator

OUT = Path("reports/phase4/report.md")
CROSS_MARGIN = lambda c: 1.10 if c in MAJORS else 1.30  # noqa: E731
PRIMARY = "P MILP"
# Sharpes of the multi-venue runs made before the switch to single-venue books (reports in git history,
# d47bd09): Phase 4 P, R1, R2, A1, A2, A3 and Phase 4b 4b-P, 4b-R1. Counted so the deflated Sharpe stays honest.
EARLIER_TRIALS = [0.67, 1.00, 1.19, 0.52, 0.19, 0.83, 1.32, 1.18]


def milp_backtest(panels, fc: pd.Series, tbill, params: Params, margin=None, costs=COSTS) -> pd.DataFrame:
    """MILP on each venue separately (NAV split 50/50); combined ledger with position and trade logs in attrs.
    ``fc`` is indexed (venue, ts, coin)."""
    books = [run_daily(panels[v], make_allocator(fc.xs(v, level="venue"), panels[v], tbill, params), NAV / len(VENUES),
                       tbill, costs[v], margin, START, v) for v in VENUES]
    logs = {k: pd.concat([b.attrs[k] for b in books], ignore_index=True) for k in ("positions", "trades", "coin_pnl")}
    for b in books:
        b.attrs = {}
    out = sum(b[["equity_start", "pnl", "n_held", "liquidations", *COMPONENTS]] for b in books)
    out = out.assign(tbill=books[0]["tbill"])
    out.attrs = logs
    return out


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc7, fc30 = walk_forward(rows), walk_forward(rows, target="target_30d")

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
        "A2 no per-coin caps": (fc30["M3_regression"], Params(per_coin_caps=False), None),
        "A3 7-day horizon": (fc7["M3_regression"], Params(horizon_days=7), None),
    }
    for name, (fc, params, margin) in runs.items():
        print(f"running {name}", flush=True)
        ledgers[name] = milp_backtest(panels, fc, tbill, params, margin)

    rets = {n: daily_excess(ld) for n, ld in ledgers.items()}
    trials = [metrics.sharpe(r) for r in rets.values()] + EARLIER_TRIALS
    out = ["# Phase 4: MILP allocator\n\n"
           f"NAV ${NAV:,.0f}, $500k on each of Binance and Bybit run as separate books, {START[:4]}-01 to "
           f"{ledgers[PRIMARY].index[-1]:%Y-%m}, same engine, costs and conservative assumptions as Phase 3. "
           "Daily HiGHS solve, executed at the next close. Spec: [docs/plan.md](../../docs/plan.md). "
           "All returns in excess of the 3-month T-bill.\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=fmt) + "\n")

    table = pd.DataFrame({n: summary(ld) for n, ld in ledgers.items()}).T
    table["deflated Sharpe"] = [metrics.deflated_sharpe(rets[n], trials) for n in table.index]
    section("1. Summary (full period)", table,
            f"Deflated Sharpe counts all {len(trials)} runs: those shown plus the "
            f"{len(EARLIER_TRIALS)} earlier multi-venue "
            "MILP runs.")
    by_year = pd.DataFrame({n: r.groupby(r.index.year).sum() * 100 for n, r in rets.items()}).T
    section("2. Excess return by year (%)", by_year, "2026 is a partial year.")
    section("3. P&L attribution (% of NAV a year)",
            pd.DataFrame({n: attribution(ld) for n, ld in ledgers.items()}).T)

    stress = {}
    for n, ld in ledgers.items():
        r = rets[n]
        stress[n] = {"worst 30 days %": r.rolling(30).sum().min() * 100,
                     "liquidations": int(ld["liquidations"].sum())}
    section("4. Stress", pd.DataFrame(stress).T)

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
