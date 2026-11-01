# Cross-exchange trade: funding plus price, and alternative exits

Sensitivity analysis (not a decision). Same trades as the Phase 1 test: the top 20% of the trailing 3-day Binance–Bybit funding gap; short the perp on the higher-funding venue, long the other. Phase 1 counted funding only; here the change in the two perps' prices is included. All exits capped at 30 days. Round-trip cost 21 bp. Prices are 8-hour closes on both venues at the same timestamps.

## 1. Average trade by exit rule (2021–2026)

| exit            |   trades |   avg hold (days) |   funding bp |   price bp |   total bp |   net of cost bp |   median net bp |   share net > 0 |
|:----------------|---------:|------------------:|-------------:|-----------:|-----------:|-----------------:|----------------:|----------------:|
| fixed_7d        | 33707.00 |              7.00 |        24.94 |      -0.90 |      24.04 |             3.04 |           -4.70 |            0.43 |
| gap_closes      | 33760.00 |              1.60 |        13.87 |      -1.80 |      12.07 |            -8.93 |          -16.91 |            0.19 |
| price_converges | 33757.00 |              1.32 |         3.89 |       5.01 |       8.90 |           -12.10 |          -14.78 |            0.15 |

## 2. Net P&L per trade by year (bp, after costs)

|   year |   fixed_7d |   gap_closes |   price_converges |
|-------:|-----------:|-------------:|------------------:|
|   2021 |      34.21 |         4.63 |            -11.52 |
|   2022 |      -4.03 |       -15.04 |            -13.03 |
|   2023 |       0.19 |        -9.31 |             -8.62 |
|   2024 |       0.58 |        -7.10 |            -10.26 |
|   2025 |      -4.17 |        -7.03 |             -8.08 |
|   2026 |     -13.60 |       -20.20 |            -20.06 |

## 3. Was the high-funding perp also the expensive one at entry?

Positive: the trade shorts the richer perp, so convergence adds to the funding.

|    |   median entry price gap, shorted vs bought perp (bp) |   share of trades where the shorted perp was richer |
|---:|------------------------------------------------------:|----------------------------------------------------:|
|  0 |                                                  0.00 |                                                0.48 |

## 4. Price leg: BTC/ETH vs other coins (bp, mean)

| exit            |   others |   BTC/ETH |
|:----------------|---------:|----------:|
| fixed_7d        |    -0.93 |     -0.04 |
| gap_closes      |    -1.84 |     -0.66 |
| price_converges |     5.06 |      3.34 |
