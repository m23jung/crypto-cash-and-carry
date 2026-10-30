# Research plan

> **Active plan (2026-10-29):** Phase 1 was NO-GO on the cross-venue trade, so Phases 2–5 follow the
> [single-venue carry pivot](#pivot-plan-if-phase-1-is-no-go-single-venue-funding-carry). The original
> cross-venue plan is kept below for the record.

## Research questions

1. **Carry.** How large, persistent and regime-dependent is funding carry, measured
   **against the T-bill rate** (the opportunity cost of the cash), not against zero?
2. **Limits to arbitrage.** Why do funding rates for the same coin differ across venues?
   How often do the gaps exceed the "no-arbitrage band" implied by trading fees,
   transfer delays and margin requirements? (Analogous to covered interest parity
   deviations persisting because of bank balance-sheet constraints; Du, Tepper and Verdelhan 2018.)
3. **Allocation.** Does a mixed-integer optimiser (HiGHS) that models those frictions
   earn more, after costs, than strong naive rules (top-k funding *with hysteresis*)?
   Where does the difference come from: forecasting, lower turnover, or margin efficiency?

## Hypothesis

Funding is persistent and pays longs' demand for leverage to whoever supplies balance
sheet. Cross-venue gaps persist because moving capital is slow and costly, so the
gaps should mostly sit inside a cost band. An allocator that models the frictions
explicitly should beat naive rules mainly by trading less and using margin better,
and only secondarily through better forecasts.

**What would prove it wrong:** cross-venue gaps rarely exceed round-trip costs (nothing
for the optimiser to do), or a naive rule with hysteresis matches the optimiser after costs.

## Background: perps and the basis trade

- A **perpetual future (perp)** is a futures contract with no expiry. With no settlement
  date pulling its price to spot, a **funding payment** every 1–8 hours does the job:
  when the perp trades above spot, longs pay shorts, and vice versa.
- Binance-style formula: `funding = premium + clamp(interest − premium, ±0.05%)`, with
  `interest = 0.01%` per 8h. When the perp trades near spot, funding sits at **0.01% per 8h
  (≈11% a year)**: a floor rate, like interest on reserves.
- **Basis trade:** buy spot and short the perp in equal size. Price moves cancel; the
  position collects funding. Economically it is lending cash against crypto collateral,
  like a Treasury cash-and-carry funded in repo.
- **P&L = funding received + change in basis − fees − transfer costs − cost of capital.**
- **Risks:** funding turning negative (deleveraging events), liquidation of the short perp
  if margin runs short, exchange default (FTX 2022), stablecoin de-pegs.

## Data (free, availability checked 2026-10-28)

| Source | Coverage | Use |
|---|---|---|
| Binance USD-M (API + data.binance.vision) | Funding since 2019-09; spot and perp klines; hourly premium index; book depth at ±1–5% | Core venue; basis; cost and capacity model |
| Bybit linear (API + public archive) | Funding since ≥2021; trades | Second core venue |
| Hyperliquid (API) | Hourly funding since 2023-05, 235 perps | On-chain venue for the cross-venue comparison |
| Deribit (API) | BTC and ETH funding since 2019 | Cross-check |
| FRED `DGS3MO` | 3-month T-bill rate | Opportunity cost of capital |
| ~~OKX~~ | API returns only ~3 months of funding | Excluded |
| ~~Full order books~~ | Paid only (Tardis.dev) | Use Binance book depth instead |

### Optional extension: on-chain venues (decide after Phase 1)

| Venue | Free funding history | Why add it |
|---|---|---|
| Hyperliquid | Hourly since 2023-05, 235 perps | On-chain order book; different users and frictions |
| dYdX v4 | Hourly since its late-2023 launch (public indexer) | On-chain (Cosmos); capital moves by bridge, not exchange withdrawal |

Moving capital between an on-chain venue and Binance or Bybit costs more and takes longer
(bridging, chain confirmations) than moving it between two centralised venues. So the
no-arbitrage band should be **wider for on-chain/centralised pairs**. Comparing band widths
across venue pairs with different frictions is a direct test of research question 2. Only
2023-11 onwards would be covered.

Checked and rejected (2026-10-28): Kraken Futures (~12 months of history), Gate (180-day API
limit), Bitget (a few months), BitMEX (HTTP 403 from the author's location), OKX (~3 months).

### Optional extension: stock and commodity perps as synthetic financing (decide after Phase 1)

Since 2025, Binance and Bybit list perps on stocks, ETFs and commodities (Nvidia, SK Hynix, SOXL,
gold, crude…), contract type `TRADIFI_PERPETUAL`. They are excluded from the main crypto universe,
but they are a market in their own right: **a long stock perp is synthetic financing**, like a total
return swap. Its funding rate is the implied financing spread.

- **Question:** what financing rate do crypto venues imply for equity exposure, and how does it
  compare with SOFR or prime-broker TRS pricing? What keeps the gap open (stablecoin settlement,
  no prime-broker link, perps trading 24/7 while the stock doesn't)?
- **Data:** funding from the same APIs; daily perp prices already cached; underlying prices from Yahoo.
- **Limits:** only about 12–18 months of history, so mostly descriptive. Arbitrage needs a brokerage
  account and a crypto account (the friction itself).
- **Fit:** the author's synthetic-financing background; microstructure angle for trading roles.

## Plan

| Phase | Work | Exit criterion |
|---|---|---|
| **1. Data and descriptives** | Point-in-time universe (top ~30 coins on ≥2 venues, *including delisted*); funding, prices and basis; fee and transfer-cost table. Stats: time at the floor, persistence (half-life), cross-venue gaps, regimes, excess over T-bills | **Go/no-go:** do cross-venue gaps exceed round-trip costs often enough? If not, pivot to single-venue funding carry |
| **2. Forecasting** | Last value, EWMA, pooled AR(1); then premium index and basis features. Walk-forward, scored in bps error and economic value | Forecast fed to the allocator |
| **3. Backtest engine** | 8-hour steps; delta-neutral spot/perp pairs per venue; P&L attribution (funding, basis, fees, transfers, cost of capital); naive rules | Baseline results |
| **4. MILP allocator** | HiGHS: single-period with costs, then multi-period with transfer delays (time-expanded network). Constraints: minimum transfer size, venue exposure caps, leverage, liquidation buffer. Stress: venue default, funding flip | Main result |
| **5. Write-up** | Paper, resume line, interview notes | Done |

## Phase 1 go/no-go rule (fixed 2026-10-28, before any data was pulled)

Trade: short the perp on the higher-funding venue, long it on the lower one (delta-neutral,
no spot needed). Signal: trailing 3-day mean of the Bybit − Binance funding gap, known at
time *t*. Outcome: the gap actually collected over the next 7 days, in the signal's direction.

**GO** if, for the top quintile of |signal|, the mean collected 7-day gap exceeds the
taker round-trip cost of a perp-perp pair (4 legs ≈ 21 bp) **and** that holds in at least
4 of the 6 calendar years 2021–2026. Otherwise **NO-GO**: pivot to single-venue funding carry.

## Pivot plan if Phase 1 is NO-GO: single-venue funding carry

A NO-GO is itself a finding for research question 2: Binance–Bybit gaps are arbitraged down to
the cost band. That becomes a section of the paper. Only the cross-venue *trading* idea is dropped;
the data pipeline, universe, funding panel and MILP approach carry over.

**Trade:** on each venue, buy spot and short the perp in the same coin (cross-margined, so the spot
leg also collateralises the short). P&L = funding − T-bill cost of capital − fees ± basis change.

| | Cross-venue (current plan) | Single-venue carry (pivot) |
|---|---|---|
| Source of P&L | Funding *gap* between venues | Funding *level* vs T-bills |
| Positions | Long perp on one venue, short on the other | Long spot + short perp, same venue |
| Round-trip cost | 4 perp legs (~21 bp taker) | 2 spot + 2 perp legs (~30 bp taker; spot 0.10%) |
| Optimiser decides | When to move capital across venues | Which coins, how much, when to enter or exit; capital split across venues |
| Main risks | Gap reversal | Negative funding, liquidation of the short, exchange default |

**Research questions after the pivot**
1. Funding carry in excess of T-bills by regime: 2021 boom, 2022 bust and FTX, 2023–24 hikes, 2024+ Ethena.
2. Is funding predictable enough, after fees, to time entries and exits? (Phase 2 unchanged.)
3. Does the constrained allocator beat strong naive rules (BTC+ETH only; top-k with hysteresis; equal weight)?
4. Tail risk and what protection costs: negative-funding spells, liquidation buffer, venue caps.

**MILP formulation (HiGHS)**
- Objective: forecast funding − fees − T-bill cost of capital used.
- Binary open/close per coin with fixed fees, so it trades only when expected carry clears the cost.
- Minimum position size; liquidity cap as a share of each coin's daily volume.
- Concentration limits per coin and per venue (like prime-broker counterparty limits).
- Margin / liquidation buffer on the short leg, sized from each coin's volatility.
- Capital split between Binance and Bybit, with a minimum transfer size.

**Extra data:** spot prices and point-in-time spot listings per venue (many small coins have no spot
market on the same venue, so the investable universe shrinks; report this), plus the perp-vs-spot premium
from the Binance archive. The stock-perp extension becomes a natural closing chapter (long stock,
short perp, compare the funding with prime-broker/TRS financing).

## Phase 2 spec: funding forecasts (fixed 2026-10-29, before any forecast was run)

**Investable set at time *t*:** the coin is in that month's universe, has a spot bar on the same venue
at *t* (spot listed and trading), and has a funding payment in the window ending at *t*.

**Target:** average funding per 8h over the **next 21 windows (7 days)**, per venue and coin. Also
reported: next 3 windows (1 day) and next 90 (30 days).

**Information at *t*:** funding up to and including the window ending at *t*; prices up to the close
at *t*. Nothing later.

**Models**
| | Model | Notes |
|---|---|---|
| M0 | Floor: always 0.01% | The "do nothing clever" benchmark |
| M1 | Last value | |
| M2 | EWMA of funding | Half-life chosen from {1, 3, 7, 30} days on training data only |
| M3 | Pooled linear regression | Features: last value; EWMAs at 1, 7 and 30 days; basis at *t*; share of the last 3 days at the floor. One model across coins and venues |

**Walk-forward:** training starts 2021-01; out-of-sample from 2022-01. Refit monthly on an expanding
window, using only training rows whose 7-day target is fully observed before the refit date
(otherwise overlapping targets leak the future).

**Scoring (out of sample, per year 2022–2026):**
1. Mean absolute error of the 7-day target, bp per 8h.
2. Rank IC: Spearman correlation between forecast and realised target across investable coins at
   each *t*, averaged.
3. Economic value: realised next-7-day funding of the top quintile by forecast, versus all investable coins.

**Decision rule:** M3 goes into the allocator only if it beats the better of M1 and M2 on
out-of-sample MAE in **at least 4 of the 5 years**. Otherwise the simpler model is used: whichever
of M1 and M2 has the lower average out-of-sample MAE (clarified 2026-10-29, before any forecast was run).
No other tuning beyond M2's half-life. Coin-windows with |basis| > 20% are not investable (see decisions).

## Phase 3 spec: backtest engine (fixed 2026-10-29, before any backtest was run)

**Trade.** Per venue, hold *q* coins of spot and short *q* coins of the perp (in spot units, after
the contract multiplier). Price risk cancels. Per 8-hour window the position earns:

- **funding:** +q × perp price × funding rate (negative funding is paid)
- **basis:** −q × Δ(perp price − spot price)
- **fees and slippage** on every change in *q*

**Timing.** Decide at the close of window *t* using information up to *t* (forecasts from Phase 2's
walk-forward). Trade at the close of *t + 1* (one-window execution lag). Funding accrues to positions
held through a window's end.

**Capital.** NAV **$1M**, split 50/50 between Binance and Bybit (the split is optimised in Phase 4).
Conservative margin: **no cross-margining** (spot and perp in separate accounts), so the short perp
carries a **margin buffer of 50% of notional** (2× leverage) for every coin. Capital per position =
1.5 × spot notional. Margin is topped up **once a day**. Margin cash earns nothing; undeployed cash
earns the 3-month T-bill. Returns are reported **in excess of the T-bill**.

**Liquidations.** If a coin's perp close rises more than **40%** since the last daily top-up (the 50%
buffer minus 10 points for intra-bar wicks and maintenance margin, since only 8-hour closes are
stored), the short is liquidated: pay a **2% of notional** penalty, then sell the spot leg at the next
close with full fees (unhedged for that window). Measured 2021–26: BTC/ETH never rose more than 31%
in a day; other coins rose more than 50% on about 0.16% of coin-days.

**Costs.** Taker fees per leg: spot 0.10% (both venues), perp 0.05% (Binance) / 0.055% (Bybit),
plus 2 bp slippage per leg. A full round trip is about 0.38%.

**Liquidity cap.** Position notional ≤ 1% of the trailing 7-day average daily volume (the smaller of
spot and perp on that venue). Capacity is re-checked at $10M and $100M NAV.

**Exits.** If a held coin stops being investable (spot delisted, |basis| > 20%, missing price), it is
closed at the next available prices with full costs.

**Strategies (fixed list)**

| | Rule |
|---|---|
| S0 | Cash: T-bill only (zero excess by construction) |
| S1 | Passive majors: BTC and ETH on both venues, equal weight, always on |
| S2 | Naive top-5 per venue by M3 forecast, rebalanced weekly, no cost awareness |
| S3 | Cost-aware top-5 per venue by M3: **enter** if forecast 7-day funding > T-bill + round-trip cost amortised over 7 days; **exit** only when forecast < T-bill (hysteresis); decided every 8 hours |
| S3-EWMA | S3 using the M2 (EWMA) forecast, the robustness check from Phase 2 |

Equal weight within a venue, subject to the liquidity cap. Total deployed ≤ venue capital / 1.5.

**Sensitivity (reported separately, never used for the decision):** S3 with top-3 and top-10 per venue.
Every variant counts as a trial in the deflated Sharpe.

**Conservative by design:** taker fees, no BNB discount, 2 bp slippage per leg, no cross-margin, 50%
buffer, explicit liquidations, daily-only margin top-ups, one-window execution lag, forced exits at
full cost, idle cash credited with T-bills (raising the hurdle).

**Period.** 2022-01 to 2026-10, where Phase 2's forecasts are out of sample. 2021 is shown for S1 only.

**Reporting (per strategy, full period and by year)**
- Excess return, volatility, Sharpe, max drawdown, worst week, turnover, cost drag.
- **P&L attribution:** funding, basis, fees and slippage, cash. Components sum to the total.
- Probabilistic Sharpe ratio, and a **deflated Sharpe counting every variant run**, including
  any added later.

**Decision rule (what Phase 4 must beat)**
- Forecasting **adds value** if S3's excess Sharpe beats S1's with a paired block-bootstrap
  P(difference ≤ 0) < 0.10 **and** S3's excess return is positive in at least 3 of the 5 years.
- Phase 4's MILP benchmark is **the better of S1 and S3** on full-period excess Sharpe.
- If every strategy's full-period excess return is ≤ 0 after costs, the headline conclusion is
  that funding carry did not beat T-bills after costs in 2022–26, and Phase 4 is reframed around
  that result rather than abandoned.

## Phase 4 outline: MILP allocator (draft 2026-10-29; superseded by the spec below)

**Goal.** Beat Phase 3's benchmark, **S1 passive BTC+ETH** (Sharpe 1.01, +0.34% a year over T-bills),
out of sample in 2022–26, with the same engine, costs and conservative assumptions.

**What Phase 3 says to fix**
1. *Entry hurdle:* price each position over its expected holding period, not a fixed 7 days.
2. *Capital efficiency:* forgone T-bill interest on tied-up capital is the largest cost in every strategy.
3. *Tail risk:* liquidations come from small and young coins; cap them rather than add forecast complexity.

**Decision problem, solved once a day (HiGHS)**
- *Variables, per venue and coin:* notional x ≥ 0; binary y (position open); trade variables for
  buys and sells; per venue: capital allocated; binary for a capital transfer between venues.
- *Objective:* expected funding over a 30-day horizon (M3 forecast refit on a 30-day target) minus the
  T-bill on capital used, minus trading costs paid once on open and close, minus a small risk
  penalty for volatile and young coins.
- *Constraints:*
  - capital per venue, including the margin factor
  - minimum position size (x ≥ m·y)
  - liquidity cap (1% of 7-day ADV)
  - per-coin caps, tighter for coins listed under 90 days
  - maximum number of positions
  - per-venue exposure cap (exchange-default risk)
  - minimum transfer size and a one-day transfer delay for moving capital between venues

**Scenarios, declared up front**
- Margin: no cross-margin (factor 1.5, as Phase 3) vs cross-margin with spot counted as collateral
  (smaller factor, using coin-level haircuts).
- Stress: one venue defaults (equity there lost), a funding flip, a liquidation cascade.

**Comparisons**
- Against S1, S3 and S3-EWMA.
- Ablations, reported but not part of the decision: fixed 50/50 venue split; no per-coin caps;
  7-day horizon. These show where any gain comes from.

**Decision rule (to fix before running):** the MILP adds value if its Sharpe beats S1's with a
paired-bootstrap P < 0.10 and it is positive in at least 3 of 5 years. The deflated Sharpe counts
every Phase 3 and Phase 4 variant.

**Deliverables:** `funding/milp.py`; an engine extension so a rule can return sizes as well as coins;
`research/phase4_allocator.py`; `reports/phase4/`; `docs/phase4.md`.

## Phase 4 spec: MILP allocator (fixed 2026-10-29, before any Phase 4 run)

**Cadence.** One optimisation per day at the 00:00 UTC close, executed at the next close (08:00),
for both venues jointly. Solver: HiGHS, through `scipy.optimize.milp`.

**Forecast.** M3 refit on a **30-day** target with the same walk-forward (training rows need their
30-day target fully observed before each refit).

**Objective (dollars over a 30-day horizon, H = 30/365).** For each candidate coin and venue:
notional × (forecast funding − margin factor × T-bill − risk penalty) × H, minus costs. Buys pay the
full round trip (0.38%; entry now plus the future exit), sells pay nothing extra, so a position is only
opened if its expected carry covers its whole cost. Transfers pay one day of lost T-bill interest
plus a $10 fixed fee.

**Risk penalty (annualised, deducted from the forecast).** 0 for BTC and ETH; 3% for other coins;
10% for coins listed under 90 days.

**Constraints**
- Capital: sum of margin factor × notional ≤ venue equity minus outgoing transfers.
- Per-coin cap on new buying: 25% of venue equity for BTC and ETH, 10% for other coins, 5% for
  coins listed under 90 days; also ≤ 1% of 7-day ADV. Existing positions are not force-sold because
  of price drift.
- Minimum position size $10k (binary on/off).
- At most 12 positions in total.
- Venue exposure: no venue above 60% of NAV after transfers.
- Transfers between venues: minimum $50k; capital arrives one day later and earns nothing in transit.

**Margin scenarios**
- *Primary:* no cross-margin, margin factor 1.5 for every coin (as Phase 3).
- *Scenario:* cross-margin with spot as collateral: factor 1.10 for BTC and ETH, 1.30 for other coins.
  The 40% liquidation trigger is kept in both (conservative). S1 is also rerun under this scenario,
  so the comparison is like for like.

**Runs (every one is a trial in the deflated Sharpe, together with the 6 from Phase 3)**
| | Run |
|---|---|
| P | **MILP primary** (no cross-margin, M3 30-day forecast) |
| R1 | MILP with the EWMA forecast |
| R2 | MILP, cross-margin scenario; plus S1 under cross-margin for comparison |
| A1 | Ablation: fixed 50/50 venue split, no transfers |
| A2 | Ablation: no per-coin caps (liquidity cap only) |
| A3 | Ablation: 7-day horizon and M3 7-day forecast |

**Stress reporting.** Exchange default: largest share of NAV on one venue at any time (the loss if
that venue failed then). Worst 30-day excess return. Number of liquidations. (Synthetic funding-flip
and liquidation-cascade scenarios from the outline are replaced by the real 2022 and 2025–26 episodes.)

**Decision rule.** The MILP adds value if P's Sharpe beats S1's with paired-bootstrap
P(difference ≤ 0) < 0.10 **and** P's excess return is positive in at least 3 of the 5 years
2022–2026.


## Phase 4b spec: MILP with churn controls and realistic margin (fixed 2026-10-29, before any 4b run)

**Why.** Phase 4's diagnostic traced the MILP's 6× turnover to (a) rotations priced only on the
entry side and (b) daily dust resizes. The sensitivity study showed realistic portfolio margin for
BTC/ETH is about 1.05×, not the 1.50× worst case. Phase 4b tests the MILP with both fixed.

**Changes from the Phase 4 spec (everything else unchanged):**
1. *Turnover penalty on exits.* Buys still pay the full round trip; **sells now also pay the exit
   half** (spot + perp fee + slippage per leg). This deliberately double-counts the exit for positions
   the MILP opened itself: a conservative turnover penalty that makes rotation clear a higher bar.
2. *No-trade band.* A held position is either left unchanged or traded by at least
   **max($5k, 10% of the position)**; closing it entirely is always allowed. (Binary per held position.)
3. *Margin (primary case):* portfolio/unified margin, factor **1.05 for BTC and ETH, 1.30 for other
   coins**. Liquidation rule unchanged (conservative).

**Benchmark (like for like):** S1 passive BTC+ETH at margin factor 1.05 (Phase 3 rule, never rebalanced).

**Runs (each a trial, added to the 13 already counted):** 4b-P (M3 30-day forecast); 4b-R1 (EWMA
forecast); S1 at 1.05. Sensitivity, not counted: 4b-P at k = 0.5 transaction costs.

**Decision rule.** Phase 4b adds value if 4b-P's Sharpe beats S1-at-1.05's with paired-bootstrap
P(difference ≤ 0) < 0.10 **and** 4b-P is positive in at least 3 of the 5 years.

## Extension A spec: does the no-arbitrage band widen with frictions? (DRAFT 2026-10-30, pending review)

**Question.** Phase 1 found Binance–Bybit funding gaps sit inside the cost band. If frictions set the
band, gaps between a centralised venue and an on-chain one (Hyperliquid, dYdX), where moving capital
means bridging and chain confirmations, should be wider and slower to close.

**Pairs.** Baseline Binance–Bybit; test pairs Binance–Hyperliquid and Binance–dYdX.
**Period.** 2023-11 to 2026-10 (dYdX starts late October 2023). **Universe.** Each month's top-30 coins
listed on both venues of the pair. **Grid.** Hourly funding summed into the same 8-hour windows.

**Measures per pair and year (2024, 2025, 2026):** median and 90th-percentile |gap| (bp per 8h), gap
half-life (pooled AR(1)), funding correlation, and the Phase 1 trade (top quintile of the trailing 3-day
gap, collected over 7 days) against each pair's taker round trip (fees to be verified from venue docs).

**Pre-registered prediction.** Both CEX–DEX pairs have a larger median |gap| **and** a longer half-life
than Binance–Bybit in at least 2 of the 3 years. Otherwise frictions do not visibly widen the band.

**Caveat to report.** On-chain venues use different funding formulas and caps, so part of any gap can be
mechanical rather than an arbitrage opportunity.

## Extension B spec: stock and commodity perps as synthetic financing (fixed 2026-10-30, before any analysis)

**Question.** What financing rate do crypto venues charge for leveraged equity and commodity exposure,
and how does it compare with SOFR (the reference for prime-broker and total-return-swap financing)?

**Data.** Binance and Bybit TradFi perps (funding and 8-hour prices, 2025 onwards; already downloaded);
underlying closes from Yahoo Finance; SOFR from FRED. Descriptive only, no strategy test.

**Measures (fixed in advance).**
1. **Implied financing and break-even spread.** For each perp, the annualised funding a long pays is
   the venue's implied financing rate for synthetic exposure. The **break-even spread** is
   s* = funding − SOFR (adjusted for the change in the perp's basis to the underlying): a long holder is
   better off in the perp than in cash stock financed at SOFR + s whenever s > s*; equivalently, an
   arbitrageur long stock / short perp earns carry whenever their financing spread is below s*.
   Report the distribution of s* by asset type (single stocks, ETFs, commodities) and over time, so
   readers can compare it with their own prime-broker or TRS terms. No fixed threshold, since those
   terms vary by agreement.
2. Weekend vs weekday funding (the perp trades 24/7, the underlying does not): paired difference test.
3. Perp-vs-underlying basis at the US close, and the Binance–Bybit funding gap for TradFi perps against
   crypto perps (are these newer markets less integrated?).

**Limits to report.** About 12–18 months of history; underlying prices only at US market close.
