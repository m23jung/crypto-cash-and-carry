# Phase 4b: MILP with churn controls and realistic margin (completed 2026-10-29)

Generated tables: [`reports/phase4b/report.md`](../reports/phase4b/report.md).
Code: [`research/phase4b_allocator.py`](../research/phase4b_allocator.py); churn controls in
[`funding/milp.py`](../funding/milp.py) (`exit_cost`, `band_abs`, `band_rel`).
Single-venue books since 2026-10-31 (see [Phase 4](phase4.md)); numbers below are the single-venue rerun.
Spec and decision rule (fixed before any 4b run): [plan](plan.md#phase-4b-spec-milp-with-churn-controls-and-realistic-margin-fixed-2026-10-29-before-any-4b-run).

## Decision

**Phase 4b does not add value.** Under realistic portfolio margin the benchmark is very strong:
passive BTC+ETH at margin 1.05 earned **+1.94% a year, Sharpe 4.18**. The churn-controlled MILP earned
+1.45% at Sharpe 1.21 (difference −2.98, P(not better) = 0.99), positive in 3 of 5 years. Deflated
Sharpe 3% over 23 trials.

## Results (2022-01 to 2026-10, $1M, excess of T-bills)

| Run | Excess % a year | Sharpe | Max drawdown | Turnover × NAV | Costs % a year | Opens+closes / resizes a year |
|---|---|---|---|---|---|---|
| **S1 passive BTC+ETH, margin 1.05** (benchmark) | **1.94** | **4.18** | −1.2% | 0.2 | 0.04 | — |
| **4b-P MILP, churn controls, portfolio margin** | 1.45 | 1.21 | −2.6% | 4.2 | 0.84 | 67 / 82 |
| 4b-R1 same, EWMA forecast | 1.79 | 1.08 | −2.2% | 6.7 | 1.34 | 106 / 108 |
| Phase 4 primary (reproduced, for reference) | 0.63 | 0.55 | −1.7% | 5.2 | 1.05 | 93 / 112 |
| Sensitivity: 4b-P at half costs (not a trial) | 1.42 | 1.05 | −3.1% | 10.8 | 1.05 | 176 / 135 |

By year (% over T-bills): passive 0.67 / 1.66 / 6.90 / 0.96 / −0.80 vs 4b-P 0.22 / 0.93 / 7.11 / −0.56 / −0.69
(2022–2026). The MILP wins only in 2024 and 2026.

## What the numbers say

1. **The churn controls work as intended.** Opens and closes fell by more than a quarter (93 → 67 a
   year), resizes by a quarter, turnover from 5.2× to 4.2× and costs from 1.05% to 0.84% a year. Together
   with realistic margin the MILP's return more than doubled (0.63% → 1.45%).
2. **But realistic margin helps the passive benchmark even more.** At 1.05, BTC+ETH carry ties up
   almost no extra capital and trades almost never (costs 0.07%). Its return is about 0.5% a year above
   the MILP's with a third of the volatility, so its Sharpe is three times higher.
3. **What the MILP buys is not worth its cost.** It earns its edge in high-funding bursts (2024: +7.1%
   vs +6.9%) but pays for it in turnover and in quieter years (2025: −0.6% vs +1.0%). Moving into small
   coins brings basis losses, liquidations and a higher capital factor (1.30 vs 1.05).
4. **Cheaper execution does not rescue it.** At half costs the MILP simply trades more (turnover 10.8×)
   and ends up about where it was. The objective chases carry whenever trading is cheaper.

## Conclusion of Phases 3–4b

For 2022–2026, under realistic margin, **no forecast-driven or optimised strategy beat holding the
BTC and ETH basis trade passively.** The carry that remained after 2021 was concentrated in the
majors, earned mostly in two bursts (2024), and was small relative to the cost of rotating into
smaller coins. The decisive variables were the capital structure and costs, not selection.
