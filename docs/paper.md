# Crypto Cash-and-Carry: Capital Efficiency in the Spot–Perpetual Basis Trade

## Summary

**Question.** Buying spot crypto and shorting the perpetual future ("perp") collects the perp's funding
rate with no price exposure: economically, a secured loan of cash. Can the trade be improved by
forecasting funding, or by optimising which coins to hold and how much?

**Approach.** Free exchange data for 274 coins on Binance and Bybit (2021–2026, including later-delisted
coins), each exchange run as its own book. Every test had its decision rule written down before it ran,
and every variant is counted when judging statistical significance.

**Findings.**

- **Carry over cash collapsed after 2021.** The exchange's funding floor (10.95% a year) stayed fixed while
  T-bills rose from 0% to 5%.
- **Funding is forecastable, but the edge is about the size of trading costs.**
- **No active strategy beat holding BTC and ETH passively**, including a daily MILP optimiser.
- **Capital structure decides the outcome.** The trade breaks even at about 1.4× capital per $1 of notional.
  Under portfolio margin (about 1.05×), passive BTC+ETH earned **+1.9% a year over T-bills (Sharpe 4.2)**;
  with spot and margin held separately (1.5×), +0.4%.

![Cumulative excess return](../reports/figures/1_cumulative_excess_return.png)

*Figure 1. Cumulative return over T-bills, $1M split across both exchanges, after all costs (2022–2026).
Numbered dips are short-perp liquidations in price spikes on small coins (Section 4).*

---

## 1. Trade Mechanics

**Perpetual futures** never expire. Instead, longs and shorts exchange a **funding payment** every 1–8 hours
that pushes the perp back towards the spot price:

- Perp above spot → longs pay shorts. Perp below spot → shorts pay longs.
- Binance's formula per 8 hours: **funding = premium + clamp(0.01% − premium, ±0.05%)**.
- For any small premium, the clamp returns exactly **0.01% per 8 hours = 10.95% a year**: an
  administered **floor**, much like an interest rate set by the exchange.

**The basis (cash-and-carry) trade:** buy *q* coins of spot, short *q* coins of the perp.

| P&L component | Source |
|---|---|
| Funding | received on the short perp each period (paid when funding is negative) |
| Basis change | gain or loss as the perp–spot gap moves |
| Trading costs | fees and slippage when opening, closing or resizing |
| Cost of capital | the T-bill interest given up on cash tied up in the position |

**Margin factor** = capital tied up per $1 of notional (spot plus margin for the short):

- **1.5** if spot and the short perp sit in separate accounts with a 50% buffer (the conservative case).
- **About 1.05** under portfolio margin, where spot counts as collateral at a 95% ratio.

> **Excess return over T-bills ≈ funding ÷ margin factor − T-bill rate − trading costs.**

All results below are in excess of the 3-month T-bill, net of all costs.

## 2. Data

- **Exchanges:** Binance and Bybit (funding, daily volume, 8-hour spot and perp prices, 2021–2026);
  3-month T-bill from FRED. Each exchange is a separate $500k book: every position is spot and perp on the
  same exchange.
- **Universe:** each month, the top 30 coins by trailing Binance volume among coins on both exchanges,
  using only data available at the time: **274 coins**, including coins later delisted.
- **Investable:** in that month's universe, with a spot market on the same exchange and a perp–spot gap
  within ±20%. About **25 coins per exchange** from 2022.
- **Periods:** 2021 trains the forecasts; all backtests run 2022–2026 out of sample.
- Stock, ETF and commodity perps are excluded (Appendix A).

## 3. Funding Forecasts

**Setup** (Appendix B):

- Target: each coin's average funding over the **next 7 days**.
- Four models: a constant (the 0.01% floor), last value, an exponentially weighted average (EWMA) and a
  pooled linear regression on recent funding averages, the perp–spot gap and time spent at the floor.
- Walk-forward on an expanding window: refitted monthly on all data up to then, tested out of sample
  from 2022.

**Results** (out of sample, 2022–2026):

| | Floor | Last value | EWMA | Regression |
|---|---|---|---|---|
| Forecast error, mean absolute (bp per 8h), range over years | 1.06–2.17 | 0.96–2.00 | 0.82–1.68 | **0.72–1.39** |
| Ranking of coins: rank IC, range over years | — | 0.37–0.60 | **0.49–0.70** | 0.47–0.68 |
| Top 20% by forecast vs average coin (% a year, before costs) | — | 4.6–10.5 | 6.5–15.2 | 6.3–16.8 |

![Funding forecasts](../reports/figures/8_forecasts.png)

*Figure 2. Left: forecast error by model, 2022–2026. Middle: coins sorted each window into fifths by the
regression forecast; bars show the funding they actually earned over the next 7 days, dots the forecast.
Right: rotating weekly into the top fifth, against the average coin.*

- **The regression is the most accurate** (lowest error in 4 of 5 years) and is used downstream; the EWMA
  ranks coins slightly better.
- **Funding is clearly forecastable.** Realised funding rises steadily from the lowest forecast fifth
  (−24% a year) to the highest (+10%), and the forecasts sit close to the outcomes. A rank IC around 0.5
  is very high (Appendix B).
- **The catch is cost.** The top fifth earns about 9.7% a year more than the average coin, but about half
  of it changes each week, and replacing it at 0.38% per round trip costs about 10.4% a year. Net of
  rotation, the edge is gone.

## 4. Strategies

All four run on each exchange separately, $500k each, at margin factor 1.5 unless stated (2022–2026).

| | Signal | Enter | Exit | Decides |
|---|---|---|---|---|
| **Passive** | none | hold BTC and ETH, always | only if the coin stops being investable | n/a |
| **Naive top 5** | 7-day forecast | the 5 coins with the highest forecast | drops out of the top 5 | every 7 days |
| **Cost-aware top 5** | 7-day forecast | forecast beats T-bills plus the round-trip cost spread over 7 days | forecast falls below T-bills | every 8 hours |
| **MILP** | 30-day forecast | chosen by the optimiser, net of trading costs | chosen by the optimiser | daily |

- **Passive** is the benchmark: the basis trade on the two largest coins, no selection.
- **Naive top 5** tests the forecast with no regard for cost.
- **Cost-aware top 5** enters only when the forecast clears the T-bill plus trading cost, and exits only
  when it falls below the T-bill. The gap between the two bars stops it trading in and out.
- **MILP** (mixed-integer program, solved with HiGHS) decides daily which coins to hold and how much of
  each. It maximises expected funding over 30 days, minus the T-bill on capital used, trading costs and a
  risk penalty for small and new coins, subject to the exchange's capital, per-coin caps (25% BTC/ETH,
  10% other coins, 5% coins listed under 90 days), 1% of daily volume, a $10k minimum and 6 positions
  (Appendix D). The 30-day horizon spreads the round trip over a typical holding period, lowering the
  cost hurdle from about 20% to 4.6% a year.
- **Common rules:** forecasts are recomputed every 8 hours (the regression is refitted monthly); decisions
  are executed at the next 8-hour close; positions close on liquidation or when the coin leaves the
  universe.

**Results:**

| | Margin | Excess return a year | Sharpe | Max drawdown | Turnover (× capital a year) | Costs a year |
|---|---|---|---|---|---|---|
| **Passive BTC+ETH** | 1.50 | +0.36% | 1.10 | −2.5% | 0.1 | 0.03% |
| Naive top 5 | 1.50 | −4.31% | −1.68 | −19.0% | 31.3 | 5.95% |
| Cost-aware top 5 | 1.50 | +1.46% | 0.83 | −3.5% | 3.0 | 0.59% |
| Cost-aware top 5, EWMA forecast | 1.50 | +2.56% | 1.35 | −2.3% | 2.4 | 0.44% |
| MILP | 1.50 | +0.63% | 0.55 | −1.7% | 5.2 | 1.05% |
| MILP with turnover controls* | 1.05 / 1.30 | +1.45% | 1.21 | −2.6% | 4.2 | 0.84% |
| **Passive BTC+ETH, portfolio margin** | **1.05** | **+1.94%** | **4.18** | −1.2% | 0.2 | 0.04% |

\* *Exit costs charged in the objective, a no-trade band (trades smaller than $5k or 10% skipped), and
realistic portfolio margin (1.05 for BTC/ETH, 1.30 for other coins).*

No active strategy beats passive at the same margin on a risk-adjusted basis (cost-aware rule
P(not better) = 0.51; MILP 0.66; MILP with turnover controls 0.99), and none survives the correction
for the number of variants tried (Appendix B).

**Why none of them beats passive:**

- **Naive rotation is eaten by costs:** the most funding collected (5.8% of capital a year) but 6.0% paid in
  costs and 0.6% in liquidation penalties.
- **The cost-aware rule mostly sits in cash:** a 0.38% round trip spread over 7 days requires forecast
  funding of about 24% a year to enter, so it held 1.7 coins on average out of 10 slots. Its higher return
  comes with more volatility, so its Sharpe is lower.
- **The MILP gives the carry back in trading.** It is fully invested in the high-funding periods of 2022
  and 2024 and in T-bills otherwise, but makes about 90 opens and closes a year as forecasts change.
  Turnover controls cut that to about 65 and, with portfolio margin, more than doubled
  the return, still well short of passive under the same margin.
- **Small coins bring liquidations and basis losses.** Every numbered dip in Figure 1 is a short perp
  liquidated in a price spike on a small coin: PEOPLE (March 2024), ADA (March 2025, when it jumped on the
  US "crypto strategic reserve" announcement), BNX (March 2025, −2.1% in a day, mostly reversed the next
  day) and BSB (June 2026). Each costs a 2% penalty plus a loss on the leftover spot, sold at the next
  8-hour close after the spike has partly reversed. BTC and ETH were never liquidated.
- **Capital cost is the largest drag in every strategy** (Figure 3). Passive BTC+ETH trades almost never
  and, under portfolio margin, ties up the least capital.

![Where the excess return comes from](../reports/figures/2_pnl_attribution.png)

*Figure 3. Annual P&L by source. Blue adds, red subtracts, gray is the total. "Cash − T-bill" is the
interest given up on capital tied up in positions.*

## 5. Carry Regimes

With selection ruled out, the return is the carry itself, and how much of it survived 2021 depends on the
regime:

| Year | Context | BTC funding (% a year) | Median coin funding | T-bill | Funding prints negative |
|---|---|---|---|---|---|
| 2021 | Bull market, retail leverage | 30.6 | 10.95 | 0.05 | 8% |
| 2022 | LUNA, 3AC/Celsius, FTX collapses | 4.2 | 2.9 | 2.1 | 42% |
| 2023 | Recovery; policy rate about 5% | 7.9 | 10.95 | 5.3 | 19% |
| 2024 | Spot BTC ETFs, rally | 11.9 | 10.95 | 5.2 | 13% |
| 2025 | Weaker leverage demand | 5.1 | 6.75 | 4.2 | 29% |
| 2026 (to Oct) | BTC mostly below the floor | 3.1 | 4.8 | 3.8 | 33% |

![Funding vs cost of capital](../reports/figures/3_funding_vs_capital_cost.png)

*Figure 4. Top: BTC and ETH spot prices (January 2021 = 100, log scale). Bottom: BTC funding (30-day
average) against the cost of capital. Funding spikes with rallies (2021, early and late 2024), when
leveraged buyers pay up; the trade earns only when funding is above the capital-cost line: continuously
in 2021, in bursts since.*

**Why carry compressed:**

- **The floor is set by the exchange, not by interest rates.** 10.95% a year was 11% over cash in 2021 and
  about 6% over cash once T-bills reached 5%; about 2.5% after the capital cost at margin factor 1.5.
- **Leverage demand is cyclical:** 30.6% BTC funding in 2021, negative 42% of the time in 2022.
- **The perp has traded below spot since 2022** (median −2 to −6 bp): more natural short sellers than
  leveraged buyers.
- **More arbitrage capital** (spot ETFs and Ethena's USDe stablecoin in 2024) is a likely contributor, not
  tested here.
- **Fewer coins can be hedged:** new coins increasingly list as perps only, so spot is available for only
  72–78% of the top 30 by 2026, down from 100%.

In 2021 alone, before the backtest period, passive BTC+ETH earned +12.6% over T-bills; it is not counted
in any result above, since the forecasts needed that year to train.

## 6. Margin and Cost Sensitivity

![Margin sensitivity](../reports/figures/7_margin_sensitivity.png)

*Figure 5. Passive BTC+ETH excess return against capital tied up per $1 of notional (constant exposure,
weekly rebalance). Break-even is about 1.4.*

**Margin is the main lever.**

- Each additional 0.1 of margin factor costs about 0.4–0.5% a year.
- Break-even ≈ funding ÷ (T-bill + costs) ≈ 6.4% ÷ 4.6% ≈ **1.4**.
- Exchange documentation puts realistic BTC/ETH portfolio margin at 1.0–1.05 (95% collateral ratio, 0.4%
  maintenance margin).
- Earning interest on the capital already tied up (yield-bearing collateral) would attack the largest cost
  directly.

**Costs matter most for active strategies.** All fees and slippage multiplied by k (k = 1 is the base case,
about 0.38% per round trip):

| k | 0.25 | 0.5 | 1 | 2 |
|---|---|---|---|---|
| Passive BTC+ETH (margin 1.10) | +1.56% | +1.43% | +1.18% | +0.68% |
| MILP (margin 1.50) | +1.12% | +0.82% | +0.63% | +0.28% |

Even with maker or VIP fees, the MILP stays below passive under the same margin.

## 7. Conclusion

- The carry that survived 2021 is a **financing spread**: funding near an exchange-set floor, earned against
  the cost of cash.
- It cannot be improved by coin selection (the edge is about the cost of trading it) or by a constrained
  optimiser (it gives the carry back in turnover).
- What moves returns is the balance sheet: **the margin factor, whether collateral earns interest, and
  execution cost**.

**Limitations**

- Five out-of-sample years, with most of the P&L in 2024. Low-volatility carry flatters the Sharpe ratio:
  exchange failure, stablecoin de-pegs and liquidation cascades barely appear in five years of daily data.
- 8-hour prices only; flat base-tier fees; an approximate liquidation rule; margin modelled as a single factor.
- No historical coin-borrow data, so the reverse trade (long perp, short spot) is untested.
- Neither Binance nor Bybit serves Ontario residents: this describes the market, not an accessible strategy.

---

## Appendix A. Data and Universe

- **Sources:** Binance USD-M API and bulk archive (data.binance.vision), used for delisted symbols the live
  API no longer serves; Bybit v5 API (spot only from July 2021); FRED for the T-bill, lagged one day.
- **Universe:** monthly top 30 by trailing 30-day Binance perp volume among coins traded on both exchanges on
  at least 25 of the previous 30 days. Stablecoins excluded. Stock, ETF and commodity perps (Binance tag
  `TRADIFI_PERPETUAL`) excluded; by 2026 they held about a third of top-30 volume.
- **Common grid:** exchanges settle some coins every 1 or 4 hours, so all funding is summed into 8-hour
  windows ending 00:00, 08:00 and 16:00 UTC. Prices are 8-hour closes; perp prices are divided by contract
  multipliers (e.g. 1000PEPE).
- **Investable:** spot market on the same exchange, and a perp–spot gap within ±20% (larger gaps are
  collapses or broken pairs, e.g. LUNA in May 2022). Under 0.5% of windows are missing.

## Appendix B. Research Protocol

**Pre-registration.** Each test's design and pass/fail rule was written down before it ran:

| Test | Rule | Outcome |
|---|---|---|
| Forecast model choice | Regression used only if it beats last value and EWMA on error in ≥ 4 of 5 years | Pass (4 of 5) |
| Forecast-driven selection | Cost-aware top 5 beats passive Sharpe (P < 0.10) and is positive in ≥ 3 of 5 years | Fail (P = 0.51) |
| MILP | Beats passive Sharpe (P < 0.10) and positive in ≥ 3 of 5 years | Fail (P = 0.66) |
| MILP with turnover controls | Beats passive at the same margin (P < 0.10), positive in ≥ 3 of 5 years | Fail (P = 0.99) |

The MILP originally allocated across both exchanges jointly and could move capital between them. Fixing
the split at 50/50 changed its return only from +0.67% to +0.60% a year, so it was simplified to one book
per exchange after these results; all earlier runs still count as trials.

**Statistics used:**

- **Paired block bootstrap:** resamples blocks of days from two strategies together, to test whether one
  Sharpe ratio is really higher than another.
- **Deflated Sharpe ratio:** the probability that a strategy's Sharpe is real after accounting for how many
  variants were tried (23 here). The best of many skill-free strategies looks good by luck; this measure
  asks whether a result beats that luck benchmark. Only passive BTC+ETH under portfolio margin survives.
- **Rank IC:** at each point in time, the correlation between how coins are ranked by forecast and how they
  rank by actual funding afterwards, averaged over time. Zero is no information; above 0.05 is useful in
  equity research; the forecasts here reach about 0.5 because funding is persistent.

**Forecast details:**

- Features: last funding; EWMAs with 1, 7 and 30-day half-lives; perp–spot gap; share of the last 3 days at
  the floor.
- The EWMA model's half-life is chosen from {1, 3, 7, 30} days at each monthly refit, using training data only.
- No look-ahead: a training row is used only if its whole target window ends before the refit date. A test
  scrambles all data after a cut-off and checks that no earlier forecast changes.

## Appendix C. Backtest Engine

- **Timing:** decide at an 8-hour close using data up to then; trade at the next close.
- **P&L per window:** funding + basis change + cash interest − costs − liquidation penalties. The components
  add up to the equity change exactly (tested).
- **Costs (base tier, taker):** spot 0.10%; perp 0.05% (Binance), 0.055% (Bybit); plus 2 bp slippage per
  leg: about 0.38% per round trip.
- **Margin:** 50% buffer on the short, no cross-margining (margin factor 1.5) unless stated; margin topped up
  once a day.
- **Liquidation:** if the perp rises more than 40% since the last daily top-up, the short is closed with a 2%
  penalty and the spot is sold at the next close.
- **Exits:** coins that stop being investable are closed with full costs; coins with no price for 3 days
  (delisted) are closed at their last prices.
- **Liquidity:** positions capped at 1% of 7-day average daily volume.

## Appendix D. MILP Formulation

Solved separately for each exchange, with capital C. For each candidate coin, with current notional x⁰ and
forecast annual funding f:

- **Variables:** target notional x ≥ 0; buys b ≥ 0; sells s ≥ 0 (s ≤ x⁰); open position y ∈ {0, 1}.
- **Objective (maximise, over a horizon H of 30 days):**
  Σ x · (f − m·r − penalty) · H − Σ b · round-trip cost,
  where m is the margin factor, r the T-bill rate, and the penalty is 0% (BTC/ETH), 3% (other coins) or 10%
  (coins listed under 90 days) a year.
- **Constraints:**
  - x = x⁰ + b − s;
  - x ≤ cap · y and x ≥ $10k · y, where cap = min(per-coin share of C, 1% of daily volume);
  - Σ y ≤ 6;
  - Σ m · x ≤ C.
- **Turnover-controlled version:** sells also pay the exit half of the round trip, and each held position either
  stays unchanged or trades by at least max($5k, 10% of the position). A buy-or-sell binary per coin stops a
  same-day buy and sell from meeting that minimum while barely moving the position.
- Solved daily with HiGHS (via `scipy.optimize.milp`); positions left unchanged are held as is rather than
  re-traded as prices drift.

## Appendix E. Corrections

Errors found after first results were fixed, tested and rerun; no decision changed.

| Found by | Problem | Effect of the fix |
|---|---|---|
| Engine refactor | A coin with spot but no perp price produced undefined equity, silently dropping months of one variant | EWMA variant Sharpe 2.34 → 1.35 |
| 30-day forecasts | Look-ahead gap hard-coded to 7 days | Prevented a leak before any 30-day result |
| Position charts | Delisted coins (e.g. MATIC after its rename) held forever with no price | Active strategies improved |
| Trade counts | Optimiser positions re-traded as prices drifted | MILP resizes fell from ~615 to ~105 a year |
| Data end date | Final window lacked a funding print, forcing an artificial exit | Passive Sharpe 1.01 → 1.10 |
| Unit test | The no-trade band could be met by buying and selling the same coin on one day | Fixed with a buy-or-sell binary |

## Appendix F. Reproduction

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python research/build_data.py              # data (~1.5 h the first time; resumable)
.venv/bin/python research/phase1_descriptives.py     # descriptives (funding regimes, floor, coverage)
.venv/bin/python research/phase2_forecast.py         # investable set, forecasts
.venv/bin/python research/phase3_backtest.py         # coin-selection rules
.venv/bin/python research/phase4_allocator.py        # MILP
.venv/bin/python research/phase4b_allocator.py       # MILP with turnover controls
.venv/bin/python research/sensitivity.py             # margin and costs (also leverage, not in the paper)
.venv/bin/python research/figures.py                 # figures
.venv/bin/pytest                                     # tests
```

Detailed write-ups per stage: `docs/phase1.md` to `docs/phase4b.md`, `docs/sensitivity.md`. Decision rules: `docs/plan.md`. Every decision and correction: `docs/decisions.md`.
