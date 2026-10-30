# Phase 2: investable set, basis and funding forecasts

Spec and decision rule fixed in advance: [docs/plan.md](../../docs/plan.md#phase-2-spec-funding-forecasts-fixed-2026-10-29-before-any-forecast-was-run). Out-of-sample period 2022-01 onwards.

## 1. Investable set

Share of universe coin-windows with a spot market on the same venue, and investable after dropping |basis| > 20% prints.

|   bucket |   binance % with spot |   binance % investable |   binance avg investable coins |   bybit % with spot |   bybit % investable |   bybit avg investable coins |
|---------:|----------------------:|-----------------------:|-------------------------------:|--------------------:|---------------------:|-----------------------------:|
|     2021 |                 100.0 |                  100.0 |                           12.8 |                46.7 |                 46.7 |                          6.0 |
|     2022 |                  99.4 |                   99.4 |                           29.8 |                88.7 |                 88.7 |                         26.6 |
|     2023 |                 100.0 |                  100.0 |                           30.0 |                86.4 |                 86.4 |                         25.9 |
|     2024 |                  93.1 |                   93.1 |                           27.9 |                90.4 |                 90.3 |                         27.1 |
|     2025 |                  85.6 |                   85.6 |                           25.7 |                84.1 |                 84.0 |                         25.2 |
|     2026 |                  78.1 |                   77.9 |                           23.4 |                71.5 |                 71.4 |                         21.4 |

Coins with the most windows removed by the 20% basis rule (window counts):

| coin   |   binance |   bybit |
|:-------|----------:|--------:|
| VANRY  |        16 |       0 |
| ALPACA |         4 |       0 |
| LUNA   |         2 |       0 |
| BNX    |         1 |       0 |
| ALGO   |         0 |       1 |
| SOL    |         0 |       1 |

## 2. Basis (perp / spot − 1) on investable coins

Negative means the perp trades below spot; a short-perp/long-spot position entered then pays that discount back if the basis converges.

|   ts |   binance median (bp) |   binance 5th pct (bp) |   binance 95th pct (bp) |   bybit median (bp) |   bybit 5th pct (bp) |   bybit 95th pct (bp) |
|-----:|----------------------:|-----------------------:|------------------------:|--------------------:|---------------------:|----------------------:|
| 2021 |                  3.32 |                 -10.09 |                   16.85 |                2.28 |               -47.29 |                 29.35 |
| 2022 |                 -6.12 |                 -16.80 |                    2.78 |               -5.42 |               -28.59 |                 14.28 |
| 2023 |                 -3.69 |                 -14.24 |                   11.40 |               -2.92 |               -16.66 |                 15.11 |
| 2024 |                 -1.90 |                 -10.22 |                   11.67 |               -2.95 |               -12.89 |                 14.97 |
| 2025 |                 -4.94 |                 -13.49 |                    3.66 |               -5.27 |               -14.13 |                  3.77 |
| 2026 |                 -5.74 |                 -21.40 |                    4.75 |               -6.01 |               -14.63 |                  1.85 |

## 3. Forecast error: 7-day mean funding (MAE, bp per 8h, out of sample)

Lower is better. M2's half-life is re-chosen at each monthly refit on training data only.

|   ts |   M0_floor |   M1_last |   M2_ewma |   M3_regression |
|-----:|-----------:|----------:|----------:|----------------:|
| 2022 |      1.569 |     1.319 |     1.049 |           0.954 |
| 2023 |      1.056 |     1.039 |     0.886 |           0.941 |
| 2024 |      1.093 |     0.957 |     0.822 |           0.817 |
| 2025 |      1.213 |     1.194 |     0.943 |           0.721 |
| 2026 |      2.170 |     1.995 |     1.683 |           1.389 |

M2 half-life chosen most often, by year: 2022: 3d, 2023: 3d, 2024: 1d, 2025: 1d, 2026: 1d

## 4. Rank IC (Spearman, across investable coins at each time, mean by year)

|   ts |   M1_last |   M2_ewma |   M3_regression |
|-----:|----------:|----------:|----------------:|
| 2022 |     0.598 |     0.704 |           0.675 |
| 2023 |     0.514 |     0.604 |           0.501 |
| 2024 |     0.462 |     0.567 |           0.545 |
| 2025 |     0.365 |     0.485 |           0.506 |
| 2026 |     0.373 |     0.495 |           0.474 |

## 5. Economic value: realised 7-day funding, top fifth by forecast minus all coins (% a year)

|   ts |   M1_last |   M2_ewma |   M3_regression |
|-----:|----------:|----------:|----------------:|
| 2022 |      8.74 |     11.93 |           11.81 |
| 2023 |      5.77 |      7.02 |            7.16 |
| 2024 |      4.63 |      6.49 |            6.25 |
| 2025 |      5.01 |      7.24 |            8.23 |
| 2026 |     10.54 |     15.19 |           16.79 |

## 6a. Diagnostics: MAE by state (bp per 8h, all years)

| state       |   share of rows % |   M0_floor |   M1_last |   M2_ewma |   M3_regression |
|:------------|------------------:|-----------:|----------:|----------:|----------------:|
| 0 to floor  |             24.03 |       0.87 |      0.57 |      0.51 |            0.51 |
| above floor |              7.42 |       2.10 |      1.77 |      1.47 |            1.58 |
| at floor    |             42.70 |       0.61 |      0.61 |      0.56 |            0.64 |
| negative    |             25.84 |       2.86 |      2.79 |      2.16 |            1.63 |

## 6b. Diagnostics: MAE by listing age (bp per 8h, all years)

| listing age   |   share of rows % |   M0_floor |   M1_last |   M2_ewma |   M3_regression |
|:--------------|------------------:|-----------:|----------:|----------:|----------------:|
| < 90 days     |              5.22 |       2.05 |      2.28 |      2.03 |            1.70 |
| 90-365 days   |             18.23 |       1.88 |      1.70 |      1.37 |            1.25 |
| > 1 year      |             76.55 |       1.20 |      1.07 |      0.88 |            0.81 |

**Decision (rule fixed in advance):** M3 beats the better of M1/M2 in 4 of 5 years (need 4). **Model used downstream: M3_regression.**
