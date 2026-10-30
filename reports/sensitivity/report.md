# Sensitivity: capital structure and transaction costs

2022-01 to 2026-10, $1M NAV across Binance and Bybit, all returns in excess of the T-bill (average 4.12%). Not strategy tests: assumptions varied around decided strategies, so these runs are not counted as trials.

## A. Margin factor (passive BTC+ETH, constant exposure, unlevered)

Margin factor = capital tied up per $1 of notional. 1.0-1.05 matches portfolio/unified margin with spot counted at a 95% collateral ratio; 1.5 is separate accounts with a 50% buffer.

|   margin |   excess % a year |   Sharpe |   max drawdown % |   worst 30 days % |   funding % NAV a year |   costs % NAV a year |   cash − T-bill % NAV a year |
|---------:|------------------:|---------:|-----------------:|------------------:|-----------------------:|---------------------:|-----------------------------:|
|     1.00 |              1.71 |     2.83 |            -2.14 |             -1.10 |                   6.44 |                 0.55 |                        -4.14 |
|     1.05 |              1.43 |     2.49 |            -2.11 |             -1.06 |                   6.13 |                 0.53 |                        -4.14 |
|     1.10 |              1.18 |     2.15 |            -2.08 |             -1.03 |                   5.85 |                 0.50 |                        -4.14 |
|     1.20 |              0.74 |     1.47 |            -2.32 |             -0.96 |                   5.37 |                 0.46 |                        -4.14 |
|     1.30 |              0.36 |     0.78 |            -2.67 |             -0.91 |                   4.95 |                 0.43 |                        -4.14 |
|     1.50 |             -0.24 |    -0.59 |            -3.22 |             -0.82 |                   4.29 |                 0.37 |                        -4.14 |
|     1.75 |             -0.80 |    -2.31 |            -4.40 |             -0.74 |                   3.68 |                 0.32 |                        -4.14 |
|     2.00 |             -1.21 |    -4.04 |            -6.20 |             -0.67 |                   3.22 |                 0.28 |                        -4.14 |

## B. Leverage on the spot leg (margin factor 1.05)

Notional = leverage × equity / 1.05; the part above equity is borrowed at the stated annual rate (held constant, a simplification: exchange borrow rates rise when funding rises).

|                                                     |   excess % a year |   Sharpe |   max drawdown % |   worst 30 days % |   funding % NAV a year |   costs % NAV a year |   cash − T-bill % NAV a year |
|:----------------------------------------------------|------------------:|---------:|-----------------:|------------------:|-----------------------:|---------------------:|-----------------------------:|
| ('T-bill + 1% (institutional / repo-like)', '1.0x') |              1.41 |     2.45 |            -2.12 |             -1.07 |                   6.13 |                 0.53 |                        -4.16 |
| ('T-bill + 1% (institutional / repo-like)', '1.5x') |              1.65 |     1.90 |            -3.44 |             -1.68 |                   9.19 |                 0.79 |                        -6.70 |
| ('T-bill + 1% (institutional / repo-like)', '2.0x') |              1.86 |     1.61 |            -5.15 |             -2.30 |                  12.24 |                 1.05 |                        -9.26 |
| ('T-bill + 1% (institutional / repo-like)', '3.0x') |              2.28 |     1.31 |            -8.51 |             -3.54 |                  18.36 |                 1.57 |                       -14.40 |
| ('11% (exchange USDT loan)', '1.0x')                |              1.28 |     2.23 |            -2.18 |             -1.08 |                   6.13 |                 0.53 |                        -4.29 |
| ('11% (exchange USDT loan)', '1.5x')                |             -1.31 |    -1.52 |            -8.24 |             -1.92 |                   9.20 |                 0.79 |                        -9.66 |
| ('11% (exchange USDT loan)', '2.0x')                |             -4.05 |    -3.51 |           -17.75 |             -2.77 |                  12.26 |                 1.04 |                       -15.19 |
| ('11% (exchange USDT loan)', '3.0x')                |             -9.55 |    -5.52 |           -36.81 |             -4.49 |                  18.38 |                 1.58 |                       -26.25 |

## C. Transaction costs (fees + slippage × k)

k = 1 is the conservative base case (taker fees, 2 bp slippage per leg, ~0.38% round trip); k = 0.5 is roughly maker execution or a VIP fee tier; k = 0 isolates gross carry.

|                                               |   excess % a year |   Sharpe |   max drawdown % |   worst 30 days % |   funding % NAV a year |   costs % NAV a year |   cash − T-bill % NAV a year |
|:----------------------------------------------|------------------:|---------:|-----------------:|------------------:|-----------------------:|---------------------:|-----------------------------:|
| ('0.25', 'MILP primary (margin 1.50)')        |              1.06 |     0.96 |            -1.62 |             -1.34 |                   3.31 |                 1.06 |                        -1.07 |
| ('0.50', 'MILP primary (margin 1.50)')        |              0.82 |     0.79 |            -1.56 |             -1.21 |                   2.99 |                 1.15 |                        -0.89 |
| ('1.00', 'MILP primary (margin 1.50)')        |              0.67 |     0.67 |            -1.50 |             -1.26 |                   2.35 |                 1.07 |                        -0.60 |
| ('2.00', 'MILP primary (margin 1.50)')        |              0.31 |     0.62 |            -1.14 |             -0.83 |                   1.47 |                 0.65 |                        -0.34 |
| ('0.00', 'Passive BTC+ETH (margin 1.10)')     |              1.68 |     3.12 |            -1.88 |             -0.92 |                   5.85 |                 0.00 |                        -4.14 |
| ('0.25', 'Passive BTC+ETH (margin 1.10)')     |              1.56 |     2.89 |            -1.93 |             -0.95 |                   5.85 |                 0.13 |                        -4.14 |
| ('0.50', 'Passive BTC+ETH (margin 1.10)')     |              1.43 |     2.65 |            -1.98 |             -0.98 |                   5.85 |                 0.25 |                        -4.14 |
| ('1.00', 'Passive BTC+ETH (margin 1.10)')     |              1.18 |     2.15 |            -2.08 |             -1.03 |                   5.85 |                 0.50 |                        -4.14 |
| ('1.50', 'Passive BTC+ETH (margin 1.10)')     |              0.93 |     1.65 |            -2.28 |             -1.08 |                   5.85 |                 0.75 |                        -4.14 |
| ('2.00', 'Passive BTC+ETH (margin 1.10)')     |              0.68 |     1.16 |            -2.65 |             -1.13 |                   5.86 |                 1.01 |                        -4.14 |
| ('0.00', 'S3 cost-aware top-5 (margin 1.50)') |              2.05 |     0.87 |            -3.60 |             -3.58 |                   6.22 |                 0.00 |                        -3.33 |
| ('0.25', 'S3 cost-aware top-5 (margin 1.50)') |              0.88 |     0.38 |            -6.10 |             -4.29 |                   5.15 |                 1.11 |                        -2.05 |
| ('0.50', 'S3 cost-aware top-5 (margin 1.50)') |              1.05 |     0.45 |            -4.43 |             -3.52 |                   3.63 |                 0.74 |                        -1.19 |
| ('1.00', 'S3 cost-aware top-5 (margin 1.50)') |              1.46 |     0.83 |            -3.51 |             -3.46 |                   3.11 |                 0.59 |                        -0.79 |
| ('1.50', 'S3 cost-aware top-5 (margin 1.50)') |              0.86 |     0.58 |            -1.96 |             -1.92 |                   2.21 |                 0.43 |                        -0.52 |
| ('2.00', 'S3 cost-aware top-5 (margin 1.50)') |              0.77 |     0.65 |            -1.68 |             -1.63 |                   1.58 |                 0.31 |                        -0.34 |
