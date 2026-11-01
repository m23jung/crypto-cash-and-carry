# Phase 4: MILP allocator

NAV $1,000,000, $500k on each of Binance and Bybit run as separate books, 2022-01 to 2026-10, same engine, costs and conservative assumptions as Phase 3. Daily HiGHS solve, executed at the next close. Spec: [docs/plan.md](../../docs/plan.md). All returns in excess of the 3-month T-bill.

## 1. Summary (full period)

Deflated Sharpe counts all 20 runs: those shown plus the 8 earlier multi-venue MILP runs.

|                          |   excess return % a year |   volatility % a year |   Sharpe |   max drawdown % |   worst week % |   turnover x NAV a year |   cost drag % a year |   liquidations |   avg positions |   PSR |   deflated Sharpe |
|:-------------------------|-------------------------:|----------------------:|---------:|-----------------:|---------------:|------------------------:|---------------------:|---------------:|----------------:|------:|------------------:|
| S1 passive BTC+ETH       |                     0.36 |                  0.33 |     1.10 |            -2.45 |          -0.19 |                    0.12 |                 0.03 |           0.00 |            4.00 |  1.00 |              0.04 |
| S2 naive top-5           |                    -4.31 |                  2.56 |    -1.68 |           -18.98 |          -2.41 |                   31.27 |                 5.95 |          14.00 |            9.64 |  0.00 |              0.00 |
| S3 cost-aware top-5      |                     1.46 |                  1.76 |     0.83 |            -3.51 |          -1.33 |                    3.02 |                 0.59 |           7.00 |            1.70 |  0.96 |              0.02 |
| S3-EWMA top-5            |                     2.56 |                  1.90 |     1.35 |            -2.25 |          -0.59 |                    2.37 |                 0.44 |           8.00 |            1.78 |  1.00 |              0.15 |
| S3 top-3 (sensitivity)   |                     1.50 |                  2.86 |     0.52 |            -5.75 |          -2.24 |                    3.67 |                 0.72 |           7.00 |            1.19 |  0.87 |              0.00 |
| S3 top-10 (sensitivity)  |                     1.36 |                  0.96 |     1.42 |            -1.76 |          -0.65 |                    2.18 |                 0.42 |           9.00 |            2.70 |  1.00 |              0.21 |
| S1 passive, cross-margin |                     1.71 |                  0.44 |     3.85 |            -1.25 |          -0.25 |                    0.16 |                 0.04 |           0.00 |            4.00 |  1.00 |              1.00 |
| P MILP                   |                     0.63 |                  1.14 |     0.55 |            -1.74 |          -0.58 |                    5.23 |                 1.05 |           4.00 |            1.93 |  0.89 |              0.00 |
| R1 MILP, EWMA forecast   |                     1.52 |                  1.68 |     0.90 |            -2.15 |          -0.61 |                    6.69 |                 1.34 |           9.00 |            2.92 |  0.98 |              0.02 |
| R2 MILP, cross-margin    |                     1.27 |                  1.13 |     1.13 |            -1.65 |          -0.18 |                    6.33 |                 1.26 |           3.00 |            2.43 |  0.99 |              0.08 |
| A2 no per-coin caps      |                     0.89 |                  4.33 |     0.20 |            -6.59 |          -0.62 |                   10.48 |                 2.09 |           1.00 |            1.08 |  0.68 |              0.00 |
| A3 7-day horizon         |                     0.84 |                  1.14 |     0.74 |            -1.50 |          -0.48 |                    1.57 |                 0.30 |           5.00 |            0.91 |  0.94 |              0.01 |

## 2. Excess return by year (%)

2026 is a partial year.

|                          |   2022 |   2023 |   2024 |   2025 |   2026 |
|:-------------------------|-------:|-------:|-------:|-------:|-------:|
| S1 passive BTC+ETH       |   0.21 |   0.35 |   3.49 |  -0.85 |  -1.44 |
| S2 naive top-5           |  -2.89 |  -3.73 |   2.32 |  -7.09 |  -9.46 |
| S3 cost-aware top-5      |   0.13 |   0.20 |   8.51 |  -1.03 |  -0.77 |
| S3-EWMA top-5            |   0.09 |   2.37 |  10.34 |   0.33 |  -0.78 |
| S3 top-3 (sensitivity)   |   0.15 |  -0.11 |  10.08 |  -1.74 |  -1.12 |
| S3 top-10 (sensitivity)  |   0.10 |   0.61 |   6.75 |  -0.46 |  -0.44 |
| S1 passive, cross-margin |   0.60 |   1.46 |   6.40 |   0.70 |  -0.89 |
| P MILP                   |  -0.82 |   0.18 |   4.04 |  -0.12 |  -0.22 |
| R1 MILP, EWMA forecast   |  -0.33 |   1.28 |   6.99 |   0.32 |  -0.91 |
| R2 MILP, cross-margin    |  -0.49 |   0.53 |   6.53 |  -0.19 |  -0.22 |
| A2 no per-coin caps      |  -1.66 |  -0.31 |   6.19 |   0.53 |  -0.46 |
| A3 7-day horizon         |   0.03 |   0.59 |   3.95 |   0.12 |  -0.62 |

## 3. P&L attribution (% of NAV a year)

|                          |   funding |   basis |   unhedged |   costs |   liquidation |   cash minus T-bill on NAV |   total excess |
|:-------------------------|----------:|--------:|-----------:|--------:|--------------:|---------------------------:|---------------:|
| S1 passive BTC+ETH       |      3.83 |    0.01 |       0.00 |   -0.03 |         -0.00 |                      -3.45 |           0.36 |
| S2 naive top-5           |      5.78 |   -0.37 |       0.24 |   -5.95 |         -0.63 |                      -3.38 |          -4.32 |
| S3 cost-aware top-5      |      3.11 |   -0.46 |       0.43 |   -0.59 |         -0.24 |                      -0.79 |           1.46 |
| S3-EWMA top-5            |      3.60 |   -0.45 |       1.01 |   -0.44 |         -0.29 |                      -0.87 |           2.56 |
| S3 top-3 (sensitivity)   |      3.47 |   -0.72 |       0.71 |   -0.72 |         -0.38 |                      -0.86 |           1.50 |
| S3 top-10 (sensitivity)  |      2.60 |   -0.20 |       0.22 |   -0.42 |         -0.16 |                      -0.68 |           1.36 |
| S1 passive, cross-margin |      5.06 |    0.01 |       0.00 |   -0.04 |         -0.00 |                      -3.32 |           1.71 |
| P MILP                   |      2.36 |   -0.24 |       0.29 |   -1.05 |         -0.13 |                      -0.60 |           0.63 |
| R1 MILP, EWMA forecast   |      3.44 |   -0.43 |       1.01 |   -1.34 |         -0.27 |                      -0.89 |           1.52 |
| R2 MILP, cross-margin    |      3.21 |   -0.21 |       0.45 |   -1.26 |         -0.09 |                      -0.82 |           1.27 |
| A2 no per-coin caps      |      3.66 |   -1.25 |       1.50 |   -2.09 |         -0.15 |                      -0.78 |           0.89 |
| A3 7-day horizon         |      1.67 |   -0.24 |       0.20 |   -0.30 |         -0.14 |                      -0.34 |           0.84 |

## 4. Stress

|                          |   worst 30 days % |   liquidations |
|:-------------------------|------------------:|---------------:|
| S1 passive BTC+ETH       |             -0.40 |           0.00 |
| S2 naive top-5           |             -3.33 |          14.00 |
| S3 cost-aware top-5      |             -3.46 |           7.00 |
| S3-EWMA top-5            |             -2.19 |           8.00 |
| S3 top-3 (sensitivity)   |             -5.79 |           7.00 |
| S3 top-10 (sensitivity)  |             -1.73 |           9.00 |
| S1 passive, cross-margin |             -0.41 |           0.00 |
| P MILP                   |             -1.49 |           4.00 |
| R1 MILP, EWMA forecast   |             -2.01 |           9.00 |
| R2 MILP, cross-margin    |             -1.52 |           3.00 |
| A2 no per-coin caps      |             -6.10 |           1.00 |
| A3 7-day horizon         |             -1.41 |           5.00 |

## 5. Decision (rule fixed in advance)

- Sharpe difference P MILP − S1 passive BTC+ETH: **-0.54** (95% interval -2.15 to +1.84); P(difference ≤ 0) = **0.66** (need < 0.10).
- P MILP positive in **2 of 5** years (need 3).
- **The MILP adds value: NO.**
- Deflated Sharpe of P MILP over 20 trials: **0%**.
- Like-for-like under cross-margin (not part of the decision): R2 − S1 cross-margin Sharpe -2.72, P(difference ≤ 0) = 1.00.
