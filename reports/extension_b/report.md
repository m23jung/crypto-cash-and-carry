# Extension B: stock and commodity perps as synthetic financing

Binance and Bybit TradFi perps with at least 60 days of funding; underlying closes from Yahoo Finance; SOFR from FRED. Descriptive only. Spec: [docs/plan.md](../../docs/plan.md).

**Early data:** most TradFi perps listed around mid-2026, so histories are a few months long and annualised figures are early estimates.

**Break-even spread s\*** = annualised funding − SOFR − annualised change in the perp's basis to its underlying. A long holder prefers the perp to stock financed at SOFR + s whenever s > s\*; an arbitrageur (long stock, short perp) earns carry whenever their financing spread is below s\*.

## 0. Coverage

Perps per asset type and venue.

| asset_type               |   binance |   bybit |
|:-------------------------|----------:|--------:|
| ETF                      |        32 |      30 |
| commodity                |         8 |       4 |
| other (no US underlying) |        26 |       0 |
| single stock             |       112 |      98 |

## 1. Implied financing and break-even spread by asset type

Per perp over its full history, then summarised across perps. s* < 0 means the perp is *cheaper* than SOFR-financed cash exposure even before any spread.

| asset_type   |   perps |   median_days |   funding % a year (median) |   SOFR % |   s* median % |   s* 25th pct % |   s* 75th pct % |   share with s* < 0 |   median basis bp |   share of funding prints = 0 |
|:-------------|--------:|--------------:|----------------------------:|---------:|--------------:|----------------:|----------------:|--------------------:|------------------:|------------------------------:|
| ETF          |   62.00 |        112.00 |                        0.09 |     3.73 |         -2.60 |           -5.33 |            2.23 |                0.63 |              8.56 |                          0.77 |
| commodity    |   12.00 |        235.00 |                        9.95 |     3.67 |          5.99 |          -19.36 |           13.75 |                0.33 |            -12.16 |                          0.47 |
| single stock |  210.00 |        141.00 |                        3.38 |     3.71 |          1.03 |           -3.25 |            4.97 |                0.41 |             10.34 |                          0.79 |

## 1b. Perps without a US underlying (Asian equities, pre-IPO, FX): implied financing only

| asset_type               |   funding % a year |   SOFR % |   funding − SOFR % |
|:-------------------------|-------------------:|---------:|-------------------:|
| other (no US underlying) |              10.36 |     3.76 |               6.61 |

## 2. Highest and lowest break-even spreads

| coin   | venue   | asset_type   |   days |   funding % a year |   break-even spread s* % |   median basis bp |
|:-------|:--------|:-------------|-------:|-------------------:|-------------------------:|------------------:|
| BNC    | binance | single stock |    112 |              54.13 |                    55.69 |             41.32 |
| NATGAS | binance | commodity    |    212 |              53.83 |                    44.13 |            131.58 |
| BNC    | bybit   | single stock |    105 |              34.73 |                    36.60 |             26.19 |
| XAG    | binance | commodity    |    295 |              19.98 |                    17.51 |             12.40 |
| KORU   | bybit   | ETF          |    128 |              13.20 |                    16.61 |             14.87 |
| NBIS   | bybit   | single stock |    156 |              17.04 |                    16.07 |             19.70 |
| PDD    | binance | single stock |     62 |              17.06 |                    15.88 |             28.81 |
| XPD    | binance | commodity    |    272 |              19.73 |                    15.05 |             44.33 |
| IWM    | bybit   | ETF          |    143 |             -24.76 |                   -27.74 |             13.83 |
| BZ     | binance | commodity    |    212 |             -26.14 |                   -29.62 |           -187.53 |
| SKDD   | binance | ETF          |     65 |             -17.25 |                   -30.86 |             24.72 |
| CL     | binance | commodity    |    212 |             -26.48 |                   -31.49 |            -40.77 |
| TBT    | binance | ETF          |     94 |             -28.55 |                   -33.69 |             -7.86 |

## 3. Funding minus SOFR over time (monthly median across perps, % a year)

| bucket   |    ETF |   commodity |   single stock |   perps |
|:---------|-------:|------------:|---------------:|--------:|
| 2025-12  | nan    |       24.89 |         nan    |    1.00 |
| 2026-01  | nan    |       67.95 |           6.50 |    5.00 |
| 2026-02  | nan    |       34.05 |           7.86 |   12.00 |
| 2026-03  | -32.98 |        4.87 |          -2.52 |   25.00 |
| 2026-04  | -44.98 |      -12.66 |          -3.64 |   47.00 |
| 2026-05  |  11.04 |       12.40 |          17.67 |   97.00 |
| 2026-06  |  -3.40 |        2.99 |           2.90 |  173.00 |
| 2026-07  |  -3.22 |       -0.41 |          -1.93 |  248.00 |
| 2026-08  |  -3.28 |        1.04 |          -1.85 |  284.00 |
| 2026-09  |  -3.39 |        6.32 |          -1.98 |  284.00 |
| 2026-10  |  -2.72 |        3.97 |          -0.34 |  284.00 |

## 4. Weekend vs weekday funding (median across perps, % a year)

Paired across all perps: median weekend − weekday -2.25 points; Wilcoxon signed-rank p = 0.000.

| asset_type   |   weekday funding % a year |   weekend funding % a year |   diff |
|:-------------|---------------------------:|---------------------------:|-------:|
| ETF          |                       0.48 |                       0.00 |  -0.63 |
| commodity    |                       9.55 |                      11.55 |   3.70 |
| single stock |                       4.36 |                       0.98 |  -2.77 |

## 5. Integration across venues: Binance vs Bybit funding gaps

|                            |   pairs |   median |gap| bp/8h |   90th pct |gap| bp/8h |   venue correlation |   gap half-life (hours) |
|:---------------------------|--------:|---------------------:|-----------------------:|--------------------:|------------------------:|
| TradFi perps               |  132.00 |                 0.00 |                   3.14 |                0.59 |                    3.85 |
| crypto majors, same period |    5.00 |                 0.26 |                   0.81 |                0.69 |                    4.22 |
