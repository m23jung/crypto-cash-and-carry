# Extension A: does the no-arbitrage band widen with frictions?

Funding gaps between Binance and two on-chain venues (Hyperliquid, dYdX) vs the Binance–Bybit baseline on **matched** coin-windows, 2023-11 to 2026-10. Hourly funding summed into 8-hour windows. Spec: [docs/plan.md](../../docs/plan.md).

## 0. Funding by venue (universe coins)

Different floors mean part of any gap is mechanical rather than an arbitrage opportunity.

|             |   coins |   median funding % a year |   share at 0.01% floor |   share negative |
|:------------|--------:|--------------------------:|-----------------------:|-----------------:|
| binance     |  232.00 |                     10.95 |                   0.36 |             0.23 |
| bybit       |  231.00 |                     10.95 |                   0.45 |             0.22 |
| hyperliquid |  130.00 |                     10.95 |                   0.33 |             0.17 |
| dydx        |  115.00 |                      0.00 |                   0.07 |             0.18 |

## 1a. Binance–Hyperliquid vs Binance–Bybit, matched

|                                    |   coin-windows |   median |gap| bp/8h |   90th pct |gap| bp/8h |   half-life (hours) |   venue correlation |   top-quintile 7d gap bp |   round trip bp |   share of top quintile beating cost |
|:-----------------------------------|---------------:|---------------------:|-----------------------:|--------------------:|--------------------:|-------------------------:|----------------:|-------------------------------------:|
| ('Binance–Hyperliquid', 'all')     |       85295.00 |                 0.62 |                   3.40 |                5.36 |                0.85 |                    46.20 |           19.00 |                                 0.69 |
| ('Binance–Hyperliquid', 2024)      |       30766.00 |                 0.73 |                   4.55 |                3.38 |                0.78 |                    54.32 |           19.00 |                                 0.80 |
| ('Binance–Hyperliquid', 2025)      |       29282.00 |                 0.56 |                   2.32 |                4.57 |                0.90 |                    19.90 |           19.00 |                                 0.43 |
| ('Binance–Hyperliquid', 2026)      |       20243.00 |                 0.50 |                   1.65 |               11.21 |                0.93 |                    14.21 |           19.00 |                                 0.25 |
| ('Binance–Bybit (matched)', 'all') |       85295.00 |                 0.32 |                   1.63 |                5.23 |                0.91 |                    13.18 |           21.00 |                                 0.24 |
| ('Binance–Bybit (matched)', 2024)  |       30766.00 |                 0.28 |                   1.81 |                8.60 |                0.94 |                    16.39 |           21.00 |                                 0.33 |
| ('Binance–Bybit (matched)', 2025)  |       29282.00 |                 0.30 |                   1.50 |                3.59 |                0.89 |                    10.45 |           21.00 |                                 0.18 |
| ('Binance–Bybit (matched)', 2026)  |       20243.00 |                 0.37 |                   1.29 |                5.43 |                0.95 |                     2.34 |           21.00 |                                 0.06 |

## 1b. Binance–Dydx vs Binance–Bybit, matched

|                                    |   coin-windows |   median |gap| bp/8h |   90th pct |gap| bp/8h |   half-life (hours) |   venue correlation |   top-quintile 7d gap bp |   round trip bp |   share of top quintile beating cost |
|:-----------------------------------|---------------:|---------------------:|-----------------------:|--------------------:|--------------------:|-------------------------:|----------------:|-------------------------------------:|
| ('Binance–Dydx', 'all')            |       79416.00 |                 0.92 |                   3.20 |               13.68 |                0.09 |                    70.58 |           20.00 |                                 0.65 |
| ('Binance–Dydx', 2024)             |       26800.00 |                 0.99 |                   3.54 |               11.32 |                0.27 |                    61.07 |           20.00 |                                 0.71 |
| ('Binance–Dydx', 2025)             |       28656.00 |                 0.82 |                   2.74 |               11.58 |                0.07 |                    58.36 |           20.00 |                                 0.56 |
| ('Binance–Dydx', 2026)             |       20730.00 |                 0.77 |                   3.19 |               16.16 |                0.00 |                    91.60 |           20.00 |                                 0.56 |
| ('Binance–Bybit (matched)', 'all') |       79416.00 |                 0.32 |                   1.56 |                5.22 |                0.94 |                    10.18 |           21.00 |                                 0.20 |
| ('Binance–Bybit (matched)', 2024)  |       26800.00 |                 0.29 |                   1.70 |                8.86 |                0.90 |                    14.93 |           21.00 |                                 0.29 |
| ('Binance–Bybit (matched)', 2025)  |       28656.00 |                 0.30 |                   1.48 |                3.70 |                0.92 |                     9.73 |           21.00 |                                 0.16 |
| ('Binance–Bybit (matched)', 2026)  |       20730.00 |                 0.38 |                   1.42 |                5.91 |                0.95 |                     3.28 |           21.00 |                                 0.11 |

## 1c. Robustness (added after results): dYdX with Binance's 0.01% floor removed

dYdX's funding has no interest floor (median 0.00% vs 10.95% a year elsewhere), so the raw gap partly reflects the formula, not frictions. Not part of the pre-registered decision.

|                                         |   median |gap| bp/8h |   90th pct |gap| bp/8h |   half-life (hours) |   top-quintile 7d gap bp |   share of top quintile beating cost |
|:----------------------------------------|---------------------:|-----------------------:|--------------------:|-------------------------:|-------------------------------------:|
| ('Binance–Dydx, floor-adjusted', 'all') |                 0.96 |                   3.79 |               13.68 |                    87.03 |                                 0.82 |
| ('Binance–Dydx, floor-adjusted', 2024)  |                 0.91 |                   4.08 |               11.32 |                    76.78 |                                 0.82 |
| ('Binance–Dydx, floor-adjusted', 2025)  |                 1.00 |                   3.51 |               11.58 |                    78.00 |                                 0.83 |
| ('Binance–Dydx, floor-adjusted', 2026)  |                 0.96 |                   3.80 |               16.16 |                   109.18 |                                 0.78 |
| ('Binance–Bybit (matched)', 'all')      |                 0.32 |                   1.56 |                5.22 |                    10.18 |                                 0.20 |
| ('Binance–Bybit (matched)', 2024)       |                 0.29 |                   1.70 |                8.86 |                    14.93 |                                 0.29 |
| ('Binance–Bybit (matched)', 2025)       |                 0.30 |                   1.48 |                3.70 |                     9.73 |                                 0.16 |
| ('Binance–Bybit (matched)', 2026)       |                 0.38 |                   1.42 |                5.91 |                     3.28 |                                 0.11 |

## 2. Pre-registered prediction

- Binance–Hyperliquid: wider median gap **and** longer half-life than matched Binance–Bybit in **2 of 3** years (need 2).
- Binance–Dydx: wider median gap **and** longer half-life than matched Binance–Bybit in **3 of 3** years (need 2).
- **Prediction HOLDS** (both pairs must pass).
