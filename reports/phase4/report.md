# Phase 4: MILP allocator

NAV $1,000,000 across Binance and Bybit, 2022-01 to 2026-10, same engine, costs and conservative assumptions as Phase 3. Daily HiGHS solve, executed at the next close. Spec: [docs/plan.md](../../docs/plan.md). All returns in excess of the 3-month T-bill.

## 1. Summary (full period)

Deflated Sharpe counts all 13 runs (Phase 3's six, S1 under cross-margin, and Phase 4's six).

|                              |   excess return % a year |   volatility % a year |   Sharpe |   max drawdown % |   worst week % |   turnover x NAV a year |   cost drag % a year |   liquidations |   avg positions |   PSR |   deflated Sharpe |
|:-----------------------------|-------------------------:|----------------------:|---------:|-----------------:|---------------:|------------------------:|---------------------:|---------------:|----------------:|------:|------------------:|
| S1 passive BTC+ETH           |                     0.36 |                  0.33 |     1.10 |            -2.45 |          -0.19 |                    0.12 |                 0.03 |           0.00 |            4.00 |  1.00 |              0.02 |
| S2 naive top-5               |                    -4.31 |                  2.56 |    -1.68 |           -18.98 |          -2.41 |                   31.27 |                 5.95 |          14.00 |            9.64 |  0.00 |              0.00 |
| S3 cost-aware top-5          |                     1.46 |                  1.76 |     0.83 |            -3.51 |          -1.33 |                    3.02 |                 0.59 |           7.00 |            1.70 |  0.96 |              0.01 |
| S3-EWMA top-5                |                     2.56 |                  1.90 |     1.35 |            -2.25 |          -0.59 |                    2.37 |                 0.44 |           8.00 |            1.78 |  1.00 |              0.08 |
| S3 top-3 (sensitivity)       |                     1.50 |                  2.86 |     0.52 |            -5.75 |          -2.24 |                    3.67 |                 0.72 |           7.00 |            1.19 |  0.87 |              0.00 |
| S3 top-10 (sensitivity)      |                     1.36 |                  0.96 |     1.42 |            -1.76 |          -0.65 |                    2.18 |                 0.42 |           9.00 |            2.70 |  1.00 |              0.13 |
| S1 passive, cross-margin     |                     1.71 |                  0.44 |     3.85 |            -1.25 |          -0.25 |                    0.16 |                 0.04 |           0.00 |            4.00 |  1.00 |              1.00 |
| P MILP                       |                     0.67 |                  0.99 |     0.67 |            -1.50 |          -0.40 |                    5.31 |                 1.07 |           4.00 |            1.97 |  0.93 |              0.00 |
| R1 MILP, EWMA forecast       |                     1.48 |                  1.48 |     1.00 |            -1.72 |          -0.73 |                    6.83 |                 1.38 |          10.00 |            2.91 |  0.99 |              0.01 |
| R2 MILP, cross-margin        |                     1.17 |                  0.98 |     1.19 |            -1.39 |          -0.19 |                    6.39 |                 1.28 |           4.00 |            2.47 |  0.99 |              0.04 |
| A1 fixed 50/50, no transfers |                     0.60 |                  1.14 |     0.52 |            -1.73 |          -0.61 |                    5.44 |                 1.09 |           4.00 |            1.99 |  0.87 |              0.00 |
| A2 no per-coin caps          |                     0.98 |                  5.08 |     0.19 |            -7.63 |          -0.61 |                   10.35 |                 2.08 |           1.00 |            1.11 |  0.67 |              0.00 |
| A3 7-day horizon             |                     0.82 |                  0.98 |     0.83 |            -1.23 |          -0.48 |                    1.56 |                 0.30 |           5.00 |            0.91 |  0.96 |              0.01 |

## 2. Excess return by year (%)

2026 is a partial year.

|                              |   2022 |   2023 |   2024 |   2025 |   2026 |
|:-----------------------------|-------:|-------:|-------:|-------:|-------:|
| S1 passive BTC+ETH           |   0.21 |   0.35 |   3.49 |  -0.85 |  -1.44 |
| S2 naive top-5               |  -2.89 |  -3.73 |   2.32 |  -7.09 |  -9.46 |
| S3 cost-aware top-5          |   0.13 |   0.20 |   8.51 |  -1.03 |  -0.77 |
| S3-EWMA top-5                |   0.09 |   2.37 |  10.34 |   0.33 |  -0.78 |
| S3 top-3 (sensitivity)       |   0.15 |  -0.11 |  10.08 |  -1.74 |  -1.12 |
| S3 top-10 (sensitivity)      |   0.10 |   0.61 |   6.75 |  -0.46 |  -0.44 |
| S1 passive, cross-margin     |   0.60 |   1.46 |   6.40 |   0.70 |  -0.89 |
| P MILP                       |  -0.85 |   0.22 |   4.19 |  -0.17 |  -0.18 |
| R1 MILP, EWMA forecast       |  -0.35 |   1.44 |   6.83 |   0.24 |  -1.00 |
| R2 MILP, cross-margin        |  -0.53 |   0.55 |   6.07 |  -0.25 |  -0.17 |
| A1 fixed 50/50, no transfers |  -0.93 |   0.20 |   3.95 |  -0.12 |  -0.22 |
| A2 no per-coin caps          |  -1.55 |  -0.31 |   6.34 |   0.68 |  -0.44 |
| A3 7-day horizon             |   0.03 |   0.59 |   3.91 |   0.09 |  -0.67 |

## 3. P&L attribution (% of NAV a year)

|                              |   funding |   basis |   unhedged |   costs |   liquidation |   cash minus T-bill on NAV |   total excess |
|:-----------------------------|----------:|--------:|-----------:|--------:|--------------:|---------------------------:|---------------:|
| S1 passive BTC+ETH           |      3.83 |    0.01 |       0.00 |   -0.03 |         -0.00 |                      -3.45 |           0.36 |
| S2 naive top-5               |      5.78 |   -0.37 |       0.24 |   -5.95 |         -0.63 |                      -3.38 |          -4.32 |
| S3 cost-aware top-5          |      3.11 |   -0.46 |       0.43 |   -0.59 |         -0.24 |                      -0.79 |           1.46 |
| S3-EWMA top-5                |      3.60 |   -0.45 |       1.01 |   -0.44 |         -0.29 |                      -0.87 |           2.56 |
| S3 top-3 (sensitivity)       |      3.47 |   -0.72 |       0.71 |   -0.72 |         -0.38 |                      -0.86 |           1.50 |
| S3 top-10 (sensitivity)      |      2.60 |   -0.20 |       0.22 |   -0.42 |         -0.16 |                      -0.68 |           1.36 |
| S1 passive, cross-margin     |      5.06 |    0.01 |       0.00 |   -0.04 |         -0.00 |                      -3.32 |           1.71 |
| P MILP                       |      2.35 |   -0.17 |       0.28 |   -1.08 |         -0.12 |                      -0.60 |           0.67 |
| R1 MILP, EWMA forecast       |      3.47 |   -0.32 |       0.91 |   -1.38 |         -0.30 |                      -0.90 |           1.48 |
| R2 MILP, cross-margin        |      3.19 |   -0.13 |       0.34 |   -1.28 |         -0.11 |                      -0.82 |           1.17 |
| A1 fixed 50/50, no transfers |      2.37 |   -0.24 |       0.29 |   -1.09 |         -0.13 |                      -0.60 |           0.60 |
| A2 no per-coin caps          |      3.74 |   -1.48 |       1.76 |   -2.08 |         -0.17 |                      -0.79 |           0.98 |
| A3 7-day horizon             |      1.64 |   -0.18 |       0.13 |   -0.30 |         -0.13 |                      -0.34 |           0.82 |

## 4. Stress

Max share on one venue = the loss if that exchange had failed at the worst moment. Phase 3 strategies keep a fixed 50/50 split.

|                              |   worst 30 days % |   liquidations |   max share of NAV on one venue % |
|:-----------------------------|------------------:|---------------:|----------------------------------:|
| S1 passive BTC+ETH           |             -0.40 |           0.00 |                             50.00 |
| S2 naive top-5               |             -3.33 |          14.00 |                             50.00 |
| S3 cost-aware top-5          |             -3.46 |           7.00 |                             50.00 |
| S3-EWMA top-5                |             -2.19 |           8.00 |                             50.00 |
| S3 top-3 (sensitivity)       |             -5.79 |           7.00 |                             50.00 |
| S3 top-10 (sensitivity)      |             -1.73 |           9.00 |                             50.00 |
| S1 passive, cross-margin     |             -0.41 |           0.00 |                             50.00 |
| P MILP                       |             -1.26 |           4.00 |                             60.55 |
| R1 MILP, EWMA forecast       |             -1.62 |          10.00 |                             61.19 |
| R2 MILP, cross-margin        |             -1.27 |           4.00 |                             60.66 |
| A1 fixed 50/50, no transfers |             -1.50 |           4.00 |                             51.86 |
| A2 no per-coin caps          |             -7.17 |           1.00 |                             60.11 |
| A3 7-day horizon             |             -1.16 |           5.00 |                             60.63 |

## 5. Decision (rule fixed in advance)

- Sharpe difference P MILP − S1 passive BTC+ETH: **-0.43** (95% interval -2.01 to +1.84); P(difference ≤ 0) = **0.63** (need < 0.10).
- P MILP positive in **2 of 5** years (need 3).
- **The MILP adds value: NO.**
- Deflated Sharpe of P MILP over 13 trials: **0%**.
- Like-for-like under cross-margin (not part of the decision): R2 − S1 cross-margin Sharpe -2.66, P(difference ≤ 0) = 1.00.
