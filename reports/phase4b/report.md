# Phase 4b: MILP with churn controls and realistic margin

NAV $1,000,000, 2022-01 to 2026-10, returns in excess of T-bills. Changes from Phase 4: exit-side turnover penalty, no-trade band (max($5k, 10%)), portfolio margin (1.05 BTC/ETH, 1.30 others). Spec: [docs/plan.md](../../docs/plan.md).

## 1. Summary (full period)

Deflated Sharpe over 16 trials (Phase 4's 13 plus the three counted here). The check and sensitivity rows are not trials.

|                                             |   excess return % a year |   volatility % a year |   Sharpe |   max drawdown % |   worst week % |   turnover x NAV a year |   cost drag % a year |   liquidations |   avg positions |   PSR |   deflated Sharpe |
|:--------------------------------------------|-------------------------:|----------------------:|---------:|-----------------:|---------------:|------------------------:|---------------------:|---------------:|----------------:|------:|------------------:|
| S1 passive BTC+ETH, margin 1.05             |                     1.94 |                  0.46 |     4.18 |            -1.18 |          -0.26 |                    0.17 |                 0.04 |           0.00 |            4.00 |  1.00 |              1.00 |
| 4b-P MILP, churn controls, portfolio margin |                     1.53 |                  1.16 |     1.32 |            -2.48 |          -1.06 |                    4.07 |                 0.82 |           5.00 |            3.08 |  0.99 |              0.02 |
| 4b-R1 same, EWMA forecast                   |                     1.79 |                  1.52 |     1.18 |            -1.84 |          -1.14 |                    7.17 |                 1.45 |          13.00 |            4.27 |  0.99 |              0.01 |
| check: Phase 4 P reproduced                 |                     0.67 |                  0.99 |     0.67 |            -1.50 |          -0.40 |                    5.31 |                 1.07 |           4.00 |            1.97 |  0.93 |            nan    |
| sensitivity: 4b-P at half costs             |                     1.49 |                  1.27 |     1.17 |            -2.86 |          -1.11 |                   10.51 |                 1.05 |           7.00 |            3.56 |  0.99 |            nan    |

## 2. Excess return by year (%)

|                                             |   2022 |   2023 |   2024 |   2025 |   2026 |
|:--------------------------------------------|-------:|-------:|-------:|-------:|-------:|
| S1 passive BTC+ETH, margin 1.05             |   0.67 |   1.66 |   6.90 |   0.96 |  -0.80 |
| 4b-P MILP, churn controls, portfolio margin |   0.31 |   0.93 |   7.54 |  -0.69 |  -0.72 |
| 4b-R1 same, EWMA forecast                   |  -0.78 |   1.90 |   8.28 |   0.41 |  -1.14 |
| check: Phase 4 P reproduced                 |  -0.85 |   0.22 |   4.19 |  -0.17 |  -0.18 |
| sensitivity: 4b-P at half costs             |   0.56 |   1.66 |   7.39 |  -1.19 |  -1.21 |

## 3. P&L attribution (% of NAV a year)

|                                             |   funding |   basis |   unhedged |   costs |   liquidation |   cash minus T-bill on NAV |   total excess |
|:--------------------------------------------|----------:|--------:|-----------:|--------:|--------------:|---------------------------:|---------------:|
| S1 passive BTC+ETH, margin 1.05             |      5.28 |    0.01 |       0.00 |   -0.04 |         -0.00 |                      -3.30 |           1.94 |
| 4b-P MILP, churn controls, portfolio margin |      3.63 |   -0.19 |       0.14 |   -0.82 |         -0.11 |                      -1.11 |           1.53 |
| 4b-R1 same, EWMA forecast                   |      4.82 |   -0.33 |       0.65 |   -1.45 |         -0.33 |                      -1.56 |           1.79 |
| check: Phase 4 P reproduced                 |      2.35 |   -0.17 |       0.28 |   -1.08 |         -0.12 |                      -0.60 |           0.67 |
| sensitivity: 4b-P at half costs             |      4.07 |   -0.16 |       0.04 |   -1.05 |         -0.18 |                      -1.23 |           1.49 |

## 4. Trading activity

|                                             |   resize a year |   opens+closes a year |   liquidation a year |   stale close a year |
|:--------------------------------------------|----------------:|----------------------:|---------------------:|---------------------:|
| 4b-P MILP, churn controls, portfolio margin |           85.14 |                 66.91 |                 1.04 |                 0.41 |
| 4b-R1 same, EWMA forecast                   |          145.21 |                109.58 |                 2.69 |                 0.41 |
| check: Phase 4 P reproduced                 |          106.06 |                 99.85 |                 0.83 |                 0.41 |
| sensitivity: 4b-P at half costs             |          155.57 |                177.11 |                 1.45 |                 0.41 |

## 5. Decision (rule fixed in advance)

- Sharpe difference 4b-P MILP, churn controls, portfolio margin − S1 passive BTC+ETH, margin 1.05: **-2.86** (95% interval -4.05 to -0.56); P(difference ≤ 0) = **0.99** (need < 0.10).
- 4b-P MILP, churn controls, portfolio margin positive in **3 of 5** years (need 3).
- **Phase 4b adds value: NO.**
- Deflated Sharpe of 4b-P MILP, churn controls, portfolio margin: **2%** over 16 trials.
