# Phase 1: funding descriptives and go/no-go

Binance and Bybit USDT perps, 2021-01-01 to 2026-10-29, funding summed into 8-hour windows. Universe: monthly top 30 by trailing Binance volume among coins on both venues, 274 distinct coins including later-delisted ones. 172,098 coin-periods with both venues.

## 0. Data coverage

Within the universe: share of 8-hour windows with no funding payment recorded, and how often each venue settled funding (payments per 8-hour window).

|   bucket |   member coin-windows |   binance % windows missing |   binance % paid every 8h |   binance % paid every 4h |   binance % paid every 1h |   bybit % windows missing |   bybit % paid every 8h |   bybit % paid every 4h |   bybit % paid every 1h |
|---------:|----------------------:|----------------------------:|--------------------------:|--------------------------:|--------------------------:|--------------------------:|------------------------:|------------------------:|------------------------:|
|     2021 |               13995.0 |                         0.0 |                     100.0 |                       0.0 |                       0.0 |                       0.0 |                   100.0 |                     0.0 |                     0.0 |
|     2022 |               32850.0 |                         0.2 |                      99.9 |                       0.0 |                       0.0 |                       0.0 |                    99.2 |                     0.0 |                     0.5 |
|     2023 |               32850.0 |                         0.0 |                      96.8 |                       3.2 |                       0.0 |                       0.0 |                    99.5 |                     0.5 |                     0.0 |
|     2024 |               32940.0 |                         0.0 |                      69.3 |                      30.7 |                       0.0 |                       0.2 |                    98.9 |                     1.1 |                     0.0 |
|     2025 |               32850.0 |                         0.3 |                      58.3 |                      39.0 |                       2.7 |                       0.5 |                    61.3 |                    32.1 |                     5.0 |
|     2026 |               27120.0 |                         0.4 |                      57.2 |                      40.6 |                       2.2 |                       0.4 |                    61.6 |                    33.4 |                     4.9 |

Coins with the most missing Bybit windows while in the universe (%):

| coin   |   % missing |
|:-------|------------:|
| ALPACA |       100   |
| VANRY  |        63.4 |
| BNX    |        47.3 |
| TON    |        17.2 |
| HIFI   |         5.4 |

## 1. Funding level vs cash (% a year)

Average funding a short perp position receives, annualised; universe is equal-weighted. The median coin column is the median 8-hour print, annualised, which is robust to squeeze-driven tails.

|   bucket |   BTC binance |   ETH binance |   universe binance |   universe binance median coin |   universe bybit |   T-bill |   universe excess over T-bill |
|---------:|--------------:|--------------:|-------------------:|-------------------------------:|-----------------:|---------:|------------------------------:|
|     2021 |         30.61 |         16.30 |              38.62 |                          10.95 |            62.75 |     0.05 |                         38.58 |
|     2022 |          4.16 |          0.79 |              -7.60 |                           2.90 |            -4.86 |     2.07 |                         -9.68 |
|     2023 |          7.87 |          8.26 |               0.72 |                          10.95 |             2.77 |     5.27 |                         -4.55 |
|     2024 |         11.92 |         12.96 |              12.68 |                          10.95 |            13.90 |     5.18 |                          7.50 |
|     2025 |          5.13 |          4.93 |             -11.66 |                           6.75 |           -10.69 |     4.21 |                        -15.87 |
|     2026 |          3.07 |          2.12 |             -27.68 |                           4.79 |           -28.81 |     3.83 |                        -31.51 |

## 2. Share of periods exactly at the 0.01% floor (%)

|   bucket |   binance BTC+ETH |   binance others |   bybit BTC+ETH |   bybit others |
|---------:|------------------:|-----------------:|----------------:|---------------:|
|     2021 |             49.78 |            52.07 |           54.87 |          46.86 |
|     2022 |             28.36 |            34.00 |           44.06 |          54.37 |
|     2023 |             37.95 |            49.08 |           48.54 |          60.34 |
|     2024 |             40.89 |            44.01 |           43.26 |          51.38 |
|     2025 |             18.26 |            37.29 |           28.17 |          48.55 |
|     2026 |              5.97 |            24.57 |            6.80 |          36.05 |

## 3. Negative funding and tails

|   bucket |   binance % negative |   bybit % negative |   binance 1st pct (bp/8h) |   binance 99th pct (bp/8h) |
|---------:|---------------------:|-------------------:|--------------------------:|---------------------------:|
|     2021 |                 7.73 |               7.19 |                     -8.06 |                      19.50 |
|     2022 |                42.38 |              32.14 |                    -13.20 |                       1.00 |
|     2023 |                19.10 |              15.42 |                    -12.67 |                       5.61 |
|     2024 |                12.84 |              12.88 |                     -6.63 |                      10.19 |
|     2025 |                29.10 |              25.23 |                    -27.06 |                       3.60 |
|     2026 |                32.83 |              31.75 |                    -79.49 |                      11.47 |

Worst Binance prints (bp per 8h):

|                                                             |   bp per 8h |
|:------------------------------------------------------------|------------:|
| (Timestamp('2026-07-07 16:00:00+0000', tz='UTC'), 'LAB')    |     -1364.8 |
| (Timestamp('2025-12-17 00:00:00+0000', tz='UTC'), 'PIPPIN') |     -1015.8 |
| (Timestamp('2025-09-10 00:00:00+0000', tz='UTC'), 'MYX')    |     -1010.1 |
| (Timestamp('2026-06-04 16:00:00+0000', tz='UTC'), 'LAB')    |      -926.1 |
| (Timestamp('2026-07-08 00:00:00+0000', tz='UTC'), 'LAB')    |      -910.4 |

## 4. Persistence (pooled AR(1))

|                                 |   AR(1) per 8h |   half-life (days) |
|:--------------------------------|---------------:|-------------------:|
| binance funding                 |          0.728 |              0.729 |
| bybit funding                   |          0.627 |              0.496 |
| cross-venue gap (bybit-binance) |          0.292 |              0.188 |

## 5. Cross-venue funding gap

Round-trip cost of a perp-perp pair (4 legs): taker 21 bp, maker 8 bp.

|   bucket |   mean |gap| bp/8h |   median |gap| bp/8h |   90th pct |gap| bp/8h |   mean |gap| % a year |   BTC+ETH mean |gap| bp/8h |   venue correlation |
|---------:|-------------------:|---------------------:|-----------------------:|----------------------:|---------------------------:|--------------------:|
|     2021 |               2.42 |                 0.74 |                   7.01 |                 26.49 |                       1.86 |                0.71 |
|     2022 |               1.16 |                 0.59 |                   2.63 |                 12.74 |                       0.68 |                0.82 |
|     2023 |               0.70 |                 0.17 |                   1.73 |                  7.64 |                       0.37 |                0.95 |
|     2024 |               0.73 |                 0.29 |                   1.91 |                  7.98 |                       0.44 |                0.95 |
|     2025 |               1.09 |                 0.31 |                   1.82 |                 11.93 |                       0.37 |                0.94 |
|     2026 |               2.13 |                 0.44 |                   3.02 |                 23.29 |                       0.32 |                0.95 |

## 6. Go/no-go: gap collected after entering on the trailing 3-day gap (bp)

Rows are quintiles of |trailing gap|. Columns 3d/7d/30d are the gap collected over that horizon in the signal's direction, before costs.

|   quintile |   abs_signal_bp |    3d |    7d |   30d |   share_7d_>_taker_cost |
|-----------:|----------------:|------:|------:|------:|------------------------:|
|          1 |            0.02 |  0.21 |  0.58 |  2.60 |                    0.02 |
|          2 |            0.14 |  0.95 |  2.10 |  7.80 |                    0.04 |
|          3 |            0.31 |  1.65 |  3.58 | 11.44 |                    0.05 |
|          4 |            0.63 |  3.29 |  6.52 | 20.10 |                    0.11 |
|          5 |            3.13 | 13.10 | 24.98 | 70.44 |                    0.41 |

Top quintile, collected 7-day gap by year (bp):

|   bucket |   mean |   count | beats_taker_cost   |
|---------:|-------:|--------:|:-------------------|
|     2021 |   55.8 |    6439 | True               |
|     2022 |   17.6 |    7554 | False              |
|     2023 |   21.1 |    4534 | True               |
|     2024 |   21.0 |    5794 | True               |
|     2025 |   20.3 |    4880 | False              |
|     2026 |    9.8 |    5206 | False              |

**Decision (rule fixed before the data): NO-GO.** Top-quintile 7-day gap 25.0 bp vs taker cost 21 bp; beats it in 3 of 6 years (need 4).
