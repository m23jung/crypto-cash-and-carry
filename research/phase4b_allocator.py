"""Phase 4b: MILP with churn controls under realistic portfolio margin. Spec: docs/plan.md, "Phase 4b spec".

Run after research/phase4_allocator.py:  python research/phase4b_allocator.py   (writes reports/phase4b/report.md)
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pandas as pd
from phase3_backtest import BASELINE, COSTS, NAV, START, STRATEGIES, YEARS, attribution, daily_excess, summary
from sensitivity import scaled

from funding import metrics
from funding.backtest import run, run_joint
from funding.dataset import VENUES, investable_rows, load, tbill_8h
from funding.forecast import walk_forward
from funding.milp import MAJORS, Params, make_allocator

OUT = Path("reports/phase4b/report.md")
PM_MARGIN = lambda c: 1.05 if c in MAJORS else 1.30  # noqa: E731  portfolio / unified margin
CHURN = Params(exit_cost=True, band_abs=5_000, band_rel=0.10)
PRIMARY, BENCH = "4b-P MILP, churn controls, portfolio margin", "S1 passive BTC+ETH, margin 1.05"


def phase4_trial_sharpes() -> list[float]:
    """Sharpes of the 13 runs already counted in Phase 4 (read from its report)."""
    text = Path("reports/phase4/report.md").read_text().split("## 2.")[0]
    return [float(row.split("|")[4]) for row in text.splitlines() if re.match(r"\| [SPRA]", row)]


def trade_counts(ledger: pd.DataFrame) -> dict:
    tr = ledger.attrs["trades"]
    years = (ledger.index[-1] - ledger.index[0]).days / 365
    kinds = tr["kind"].replace({"open": "opens+closes", "close": "opens+closes"})
    return {f"{k} a year": n / years for k, n in kinds.value_counts().items()}


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc30 = walk_forward(rows, target="target_30d")

    def milp(fc, params, margin, costs=COSTS):
        return run_joint(panels, make_allocator(fc, panels, tbill, params), NAV, tbill, costs, margin, START)

    s1_costs = {v: dataclasses.replace(c, margin_buffer=0.05) for v, c in COSTS.items()}
    books = [run(panels[v], pd.Series(dtype=float), STRATEGIES[BASELINE][0](s1_costs[v]), 2, NAV / 2, tbill,
                 s1_costs[v], START) for v in VENUES]
    cols = ["equity_start", "pnl", "n_held", "liquidations", "funding", "basis", "unhedged", "costs", "liquidation",
            "cash", "traded"]
    ledgers = {BENCH: sum(b[cols] for b in books).assign(tbill=books[0]["tbill"])}
    runs = {
        PRIMARY: (fc30["M3_regression"], CHURN, PM_MARGIN, COSTS),
        "4b-R1 same, EWMA forecast": (fc30["M2_ewma"], CHURN, PM_MARGIN, COSTS),
        "check: Phase 4 P reproduced": (fc30["M3_regression"], Params(), None, COSTS),
        "sensitivity: 4b-P at half costs": (fc30["M3_regression"], CHURN, PM_MARGIN,
                                            {v: scaled(c, 0.5) for v, c in COSTS.items()}),
    }
    for name, args in runs.items():
        print("running", name, flush=True)
        ledgers[name] = milp(*args)

    rets = {n: daily_excess(ld) for n, ld in ledgers.items()}
    counted = [PRIMARY, "4b-R1 same, EWMA forecast", BENCH]
    trials = phase4_trial_sharpes() + [metrics.sharpe(rets[n]) for n in counted]
    out = ["# Phase 4b: MILP with churn controls and realistic margin\n\n"
           f"NAV ${NAV:,.0f}, {START[:4]}-01 to {ledgers[PRIMARY].index[-1]:%Y-%m}, returns in excess of T-bills. "
           "Changes from Phase 4: exit-side turnover penalty, no-trade band (max($5k, 10%)), portfolio margin "
           "(1.05 BTC/ETH, 1.30 others). Spec: [docs/plan.md](../../docs/plan.md).\n"]

    def section(title, df, note=""):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=".2f") + "\n")

    table = pd.DataFrame({n: summary(ld) for n, ld in ledgers.items()}).T
    table["deflated Sharpe"] = [metrics.deflated_sharpe(rets[n], trials) if n in counted else float("nan")
                                for n in table.index]
    section("1. Summary (full period)", table,
            f"Deflated Sharpe over {len(trials)} trials (Phase 4's 13 plus the three counted here). The check "
            "and sensitivity rows are not trials.")
    section("2. Excess return by year (%)",
            pd.DataFrame({n: r.groupby(r.index.year).sum() * 100 for n, r in rets.items()}).T)
    section("3. P&L attribution (% of NAV a year)", pd.DataFrame({n: attribution(ld) for n, ld in ledgers.items()}).T)
    section("4. Trading activity", pd.DataFrame({n: trade_counts(ld) for n, ld in ledgers.items()
                                                 if "trades" in ld.attrs}).T.fillna(0))

    diff, (lo, hi), p = metrics.paired_sharpe_test(rets[PRIMARY], rets[BENCH])
    by_year = rets[PRIMARY].groupby(rets[PRIMARY].index.year).sum()
    positive = int((by_year.reindex(list(YEARS)) > 0).sum())
    adds = p < 0.10 and positive >= 3
    out.append(f"\n## 5. Decision (rule fixed in advance)\n\n"
               f"- Sharpe difference {PRIMARY} − {BENCH}: **{diff:+.2f}** (95% interval {lo:+.2f} to {hi:+.2f}); "
               f"P(difference ≤ 0) = **{p:.2f}** (need < 0.10).\n"
               f"- {PRIMARY} positive in **{positive} of {len(YEARS)}** years (need 3).\n"
               f"- **Phase 4b adds value: {'YES' if adds else 'NO'}.**\n"
               f"- Deflated Sharpe of {PRIMARY}: **{table.at[PRIMARY, 'deflated Sharpe']:.0%}** "
               f"over {len(trials)} trials.\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
