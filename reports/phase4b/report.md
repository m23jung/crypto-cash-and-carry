# Phase 4b: MILP with churn controls and realistic margin

NAV $1,000,000, 2022-01 to 2026-10, returns in excess of T-bills. Changes from Phase 4: exit-side turnover penalty, no-trade band (max($5k, 10%)), portfolio margin (1.05 BTC/ETH, 1.30 others). Spec: [docs/plan.md](../../docs/plan.md).

## 1. Summary (full period)

Deflated Sharpe over 23 trials (Phase 4's, the earlier multi-venue runs and the three counted here). The check and sensitivity rows are not trials.

|                                             |   excess return % a year |   volatility % a year |   Sharpe |   max drawdown % |   worst week % |   turnover x NAV a year |   cost drag % a year |   liquidations |   avg positions |   PSR |   deflated Sharpe |
|:--------------------------------------------|-------------------------:|----------------------:|---------:|-----------------:|---------------:|------------------------:|---------------------:|---------------:|----------------:|------:|------------------:|
| S1 passive BTC+ETH, margin 1.05             |                     1.94 |                  0.46 |     4.18 |            -1.18 |          -0.26 |                    0.17 |                 0.04 |           0.00 |            4.00 |  1.00 |              1.00 |
| 4b-P MILP, churn controls, portfolio margin |                     1.45 |                  1.20 |     1.21 |            -2.55 |          -0.97 |                    4.22 |                 0.84 |           4.00 |            3.08 |  0.99 |              0.03 |
| 4b-R1 same, EWMA forecast                   |                     1.79 |                  1.66 |     1.08 |            -2.16 |          -1.03 |                    6.73 |                 1.34 |          10.00 |            4.17 |  0.99 |              0.01 |
| check: Phase 4 P reproduced                 |                     0.63 |                  1.14 |     0.55 |            -1.74 |          -0.58 |                    5.23 |                 1.05 |           4.00 |            1.93 |  0.89 |            nan    |
| sensitivity: 4b-P at half costs             |                     1.42 |                  1.35 |     1.05 |            -3.10 |          -0.98 |                   10.76 |                 1.05 |           8.00 |            3.54 |  0.98 |            nan    |

## 2. Excess return by year (%)

|                                             |   2022 |   2023 |   2024 |   2025 |   2026 |
|:--------------------------------------------|-------:|-------:|-------:|-------:|-------:|
| S1 passive BTC+ETH, margin 1.05             |   0.67 |   1.66 |   6.90 |   0.96 |  -0.80 |
| 4b-P MILP, churn controls, portfolio margin |   0.22 |   0.93 |   7.11 |  -0.56 |  -0.69 |
| 4b-R1 same, EWMA forecast                   |  -0.68 |   1.93 |   8.07 |   0.44 |  -1.09 |
| check: Phase 4 P reproduced                 |  -0.82 |   0.18 |   4.04 |  -0.12 |  -0.22 |
| sensitivity: 4b-P at half costs             |   0.42 |   1.66 |   7.13 |  -1.23 |  -1.11 |

## 3. P&L attribution (% of NAV a year)

|                                             |   funding |   basis |   unhedged |   costs |   liquidation |   cash minus T-bill on NAV |   total excess |
|:--------------------------------------------|----------:|--------:|-----------:|--------:|--------------:|---------------------------:|---------------:|
| S1 passive BTC+ETH, margin 1.05             |      5.28 |    0.01 |       0.00 |   -0.04 |         -0.00 |                      -3.30 |           1.94 |
| 4b-P MILP, churn controls, portfolio margin |      3.60 |   -0.24 |       0.12 |   -0.84 |         -0.09 |                      -1.10 |           1.45 |
| 4b-R1 same, EWMA forecast                   |      4.75 |   -0.42 |       0.52 |   -1.34 |         -0.25 |                      -1.47 |           1.79 |
| check: Phase 4 P reproduced                 |      2.36 |   -0.24 |       0.29 |   -1.05 |         -0.13 |                      -0.60 |           0.63 |
| sensitivity: 4b-P at half costs             |      4.07 |   -0.24 |       0.06 |   -1.05 |         -0.20 |                      -1.22 |           1.42 |

## 4. Trading activity

|                                             |   resize a year |   opens+closes a year |   liquidation a year |   stale close a year |
|:--------------------------------------------|----------------:|----------------------:|---------------------:|---------------------:|
| 4b-P MILP, churn controls, portfolio margin |           82.03 |                 66.70 |                 0.83 |                 0.41 |
| 4b-R1 same, EWMA forecast                   |          107.51 |                105.65 |                 2.07 |                 0.41 |
| check: Phase 4 P reproduced                 |          111.86 |                 93.22 |                 0.83 |                 0.41 |
| sensitivity: 4b-P at half costs             |          135.48 |                175.66 |                 1.66 |                 0.41 |

## 5. Decision (rule fixed in advance)

- Sharpe difference 4b-P MILP, churn controls, portfolio margin − S1 passive BTC+ETH, margin 1.05: **-2.98** (95% interval -4.15 to -0.44); P(difference ≤ 0) = **0.99** (need < 0.10).
- 4b-P MILP, churn controls, portfolio margin positive in **3 of 5** years (need 3).
- **Phase 4b adds value: NO.**
- Deflated Sharpe of 4b-P MILP, churn controls, portfolio margin: **3%** over 23 trials.
