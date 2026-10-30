# Phase 3: funding-carry backtest

NAV $1,000,000 split 50/50 across Binance and Bybit, 2022-01 to 2026-10. Conservative assumptions (taker fees, 2 bp slippage per leg, 50% margin buffer with no cross-margin, explicit liquidations). Spec: [docs/plan.md](../../docs/plan.md). All returns are in excess of the 3-month T-bill.

## 1. Summary (full period)

PSR = probability the Sharpe is above zero; deflated Sharpe also accounts for all 6 strategies run.

|                         |   excess return % a year |   volatility % a year |   Sharpe |   max drawdown % |   worst week % |   turnover x NAV a year |   cost drag % a year |   liquidations |   avg positions |   PSR |   deflated Sharpe |
|:------------------------|-------------------------:|----------------------:|---------:|-----------------:|---------------:|------------------------:|---------------------:|---------------:|----------------:|------:|------------------:|
| S1 passive BTC+ETH      |                     0.36 |                  0.33 |     1.10 |            -2.45 |          -0.19 |                    0.12 |                 0.03 |           0.00 |            4.00 |  1.00 |              0.17 |
| S2 naive top-5          |                    -4.31 |                  2.56 |    -1.68 |           -18.98 |          -2.41 |                   31.27 |                 5.95 |          14.00 |            9.64 |  0.00 |              0.00 |
| S3 cost-aware top-5     |                     1.46 |                  1.76 |     0.83 |            -3.51 |          -1.33 |                    3.02 |                 0.59 |           7.00 |            1.70 |  0.96 |              0.08 |
| S3-EWMA top-5           |                     2.56 |                  1.90 |     1.35 |            -2.25 |          -0.59 |                    2.37 |                 0.44 |           8.00 |            1.78 |  1.00 |              0.36 |
| S3 top-3 (sensitivity)  |                     1.50 |                  2.86 |     0.52 |            -5.75 |          -2.24 |                    3.67 |                 0.72 |           7.00 |            1.19 |  0.87 |              0.02 |
| S3 top-10 (sensitivity) |                     1.36 |                  0.96 |     1.42 |            -1.76 |          -0.65 |                    2.18 |                 0.42 |           9.00 |            2.70 |  1.00 |              0.43 |

## 2. Excess return by year (%)

2026 is a partial year.

|                         |   2022 |   2023 |   2024 |   2025 |   2026 |
|:------------------------|-------:|-------:|-------:|-------:|-------:|
| S1 passive BTC+ETH      |   0.21 |   0.35 |   3.49 |  -0.85 |  -1.44 |
| S2 naive top-5          |  -2.89 |  -3.73 |   2.32 |  -7.09 |  -9.46 |
| S3 cost-aware top-5     |   0.13 |   0.20 |   8.51 |  -1.03 |  -0.77 |
| S3-EWMA top-5           |   0.09 |   2.37 |  10.34 |   0.33 |  -0.78 |
| S3 top-3 (sensitivity)  |   0.15 |  -0.11 |  10.08 |  -1.74 |  -1.12 |
| S3 top-10 (sensitivity) |   0.10 |   0.61 |   6.75 |  -0.46 |  -0.44 |

## 3. P&L attribution (% of NAV a year)

Funding received, basis change, unhedged spot after liquidations, trading costs, liquidation penalties, and idle cash interest minus the T-bill on the whole NAV. Sums to the excess return.

|                         |   funding |   basis |   unhedged |   costs |   liquidation |   cash minus T-bill on NAV |   total excess |
|:------------------------|----------:|--------:|-----------:|--------:|--------------:|---------------------------:|---------------:|
| S1 passive BTC+ETH      |      3.83 |    0.01 |       0.00 |   -0.03 |         -0.00 |                      -3.45 |           0.36 |
| S2 naive top-5          |      5.78 |   -0.37 |       0.24 |   -5.95 |         -0.63 |                      -3.38 |          -4.32 |
| S3 cost-aware top-5     |      3.11 |   -0.46 |       0.43 |   -0.59 |         -0.24 |                      -0.79 |           1.46 |
| S3-EWMA top-5           |      3.60 |   -0.45 |       1.01 |   -0.44 |         -0.29 |                      -0.87 |           2.56 |
| S3 top-3 (sensitivity)  |      3.47 |   -0.72 |       0.71 |   -0.72 |         -0.38 |                      -0.86 |           1.50 |
| S3 top-10 (sensitivity) |      2.60 |   -0.20 |       0.22 |   -0.42 |         -0.16 |                      -0.68 |           1.36 |

## 4. Decision (rule fixed in advance)

- Sharpe difference S3 cost-aware top-5 − S1 passive BTC+ETH: **-0.27** (95% interval -1.71 to +2.12); P(difference ≤ 0) = **0.51** (need < 0.10).
- S3 cost-aware top-5 positive in **3 of 5** years (need 3).
- **Forecasting adds value: NO.**
- Deflated Sharpe of S3 cost-aware top-5 over 6 trials: **8%** (probability its Sharpe is real after counting every variant).
- **Phase 4 benchmark: S1 passive BTC+ETH** (better full-period Sharpe of the two).

## 5. Capacity: S3 cost-aware top-5 at larger sizes

The 1%-of-daily-volume cap binds as size grows; unfilled slots stay in cash.

|       |   excess return % a year |   Sharpe |   avg positions |   cost drag % a year |
|:------|-------------------------:|---------:|----------------:|---------------------:|
| $1M   |                     1.46 |     0.83 |            1.70 |                 0.59 |
| $10M  |                     1.21 |     1.27 |            1.70 |                 0.26 |
| $100M |                     0.29 |     2.19 |            1.70 |                 0.05 |

## 6. Context: S1 passive BTC+ETH in 2021 (before forecasts exist)

Excess return 12.6%, Sharpe 10.90, max drawdown -0.4%.
