# Decisions log

Newest first. Every analysis choice that could change a result is recorded here with its date.

- **2026-10-31 (correction)** Wording fix in paper 3.1: funding gaps do not "reopen in the same direction";
  a top-20% gap has the same sign 7 days later only 51% of the time. Added a decomposition of where the
  large gaps come from (off-floor premiums, settlement-interval mismatches, small coins).

- **2026-10-31** Cross-exchange sensitivity (not a decision; exits fixed before running): Phase 1 trades
  re-evaluated including the price leg and two alternative exits (funding gap closes; prices converge),
  capped at 30 days. Price leg ≈ 0 (perps already converged at 8-hour closes); alternative exits worse
  (−8.9 and −12.1 bp net vs +3.0 bp for the fixed 7 days). Added to paper section 3.1.

- **2026-10-30** Extension A spec fixed before analysis, with a matched Binance–Bybit baseline (same
  coin-windows) and base-tier taker fees for Hyperliquid (0.045%) and dYdX (0.050%). Result: prediction
  HOLDS (Hyperliquid 2 of 3 years, dYdX 3 of 3). dYdX found to have no funding floor or dead zone, so its
  gaps are largely mechanical; a floor-adjusted robustness check (added after results, not part of the
  decision) confirmed this. Only the Hyperliquid comparison is presented as evidence about frictions.

- **2026-10-30** Extension B (stock perps) removed from the paper and README at the author's request; code,
  report and write-up kept in the repo as exploratory work.

- **2026-10-30** Extension B wording corrected: zero TradFi funding is an exchange parameter (Binance sets the
  interest term to 0% for stock perps, so the ±0.05% clamp returns exactly zero), not a consequence of
  stablecoin collateral; the stablecoin point explains why the gap to SOFR persists. Hyperliquid download
  slowed to 2 s per call after stalling on rate limits.

- **2026-10-30** Extension B reframed before analysis: break-even financing spread s* instead of a fixed
  SOFR + 100 bp threshold (prime-broker/TRS terms vary by agreement). Scope: US stocks, ETFs and the 8
  commodities as core; Asian equities, pre-IPO and FX perps funding-only (Binance only).
- **2026-10-30** Extension B cleaning rules added after a first look at the output (disclosed): funding
  counts only from a coin's Binance TradFi listing (Bybit ticker clashes with crypto coins: GME, CAT,
  PENG, WEN, MDT); basis windows beyond ±20% dropped (Yahoo split back-adjustment, e.g. KORU, CRWD); basis
  drift as a regression slope; perps without a US underlying use Binance only. Spec assumed 12–18 months
  of history; actual median is about 4 months.
- **2026-10-30** FRED requests failed after a browser User-Agent was set globally for Yahoo (FRED rejects
  it); the header is now sent to Yahoo only.

- **2026-10-30** Core panels now end at the last window with BTC funding on both core venues, so data
  downloaded later for the extensions cannot stretch them. This also removed an artifact of the old
  runs: in the final window BTC had no funding print yet, so every strategy was force-closed at the
  end, paying exit costs. Phases 1–4b, the sensitivity study and figures were rerun. Decisions
  unchanged; passive numbers rose slightly (S1 0.34% → 0.36%, Sharpe 1.01 → 1.10; S1 at margin 1.05
  1.91% → 1.94%, Sharpe 4.07 → 4.18); active strategies essentially unchanged.

- **2026-10-29 (correction 3)** Phase 4b's first run showed resizes *rising* despite the no-trade band.
  Cause: the engine re-traded positions the MILP had left unchanged, chasing a dollar target set one
  window earlier as prices moved. Fix: unchanged positions are passed as "hold"; regression test added.
  Phase 4, 4b, the sensitivity study and the figures were rerun. Decisions unchanged. Phase 4 primary
  0.50% → 0.67% a year (resizes ~615 → ~106 a year); the Phase 4 diagnosis was corrected: most "dust
  resizes" were this engine bug, while the ~100 opens/closes a year are genuine rotation.
- **2026-10-29** Phase 4b decision: does **not** add value (4b-P Sharpe 1.32 vs S1 at margin 1.05
  4.07; P = 0.99; positive in 3 of 5 years). Deflated Sharpe 3% over 16 trials.

- **2026-10-29** Sensitivity study added (margin, leverage, transaction costs; not trials). Margin
  assumption checked against venue documentation: realistic BTC/ETH margin factor about 1.0–1.05.
- **2026-10-29** Phase 4b spec fixed before any run: exit-side turnover penalty, no-trade band
  (max($5k, 10%)), portfolio margin 1.05 / 1.30 as the primary case, benchmark S1 at 1.05.

- **2026-10-29 (correction 2)** Charts revealed positions in delisted coins (MATIC after its POL
  migration, BNX) held forever with no prices, tying up capital and earning nothing. Fix: a held coin
  (or leftover spot) with no price for 3 days is closed at its last prices with full costs; regression
  test added. Phases 3 and 4 rerun. Decisions unchanged. Changes: S3 1.16% → 1.46% (Sharpe 0.66 → 0.83);
  S3-EWMA 2.27% → 2.56%; MILP 0.31% → 0.50% (Sharpe 0.38 → 0.60); passive strategies unchanged.

- **2026-10-29** Phase 4 decision: the MILP does **not** add value (Sharpe 0.38 vs S1 1.01, P = 0.75;
  positive in 2 of 5 years). Best run overall: S1 under cross-margin (+1.68% a year, Sharpe 3.74,
  deflated Sharpe 100% over 13 trials). A diagnostic rerun (instrumentation only, no change to results)
  traced the MILP's 5.9× turnover to two specification choices: exits not charged in the objective,
  and no no-trade band. A Phase 4b fixing them is listed but not run.
- **2026-10-29** Phase 4 implementation choices made before results: execution trades a coin only when
  the change exceeds $100; buys on a venue are limited to the capital actually there (a planned
  transfer may land the next day, when the next solve buys the rest); held coins with no forecast that
  day are kept unchanged.

- **2026-10-29 (correction)** Bug found while refactoring the engine for Phase 4: the engine could enter
  a coin that had a spot price but no perp price that window, producing a NaN cost and undefined equity.
  It hit only S3-EWMA's Bybit book (from 2025-02-22, ~20 months silently dropped). Fixed (both prices
  required to enter; the engine now raises if equity is ever non-finite; regression test added) and
  Phase 3 rerun. S3-EWMA: Sharpe 2.34 → **1.20**, deflated Sharpe 90% → **27%**. Decision unchanged.
- **2026-10-29** Walk-forward leakage gap now matches the target length (7 or 30 days); previously
  hard-coded to 7 days, which only mattered for the new 30-day target. Leak test extended to 30 days
  and confirmed to catch the old gap.

- **2026-10-29** Phase 4 spec fixed (before any run) with the outline's defaults, conservative end:
  caps 25% / 10% / 5% (majors / others / listed < 90 days); minimum $10k; at most 12 positions; venue
  cap 60%; cross-margin factors 1.10 / 1.30; daily rebalancing; risk penalty 0% / 3% / 10% a year.
  Solver: HiGHS via `scipy.optimize.milp` (no extra dependency). Synthetic stress scenarios replaced
  by the real 2022 and 2025–26 episodes.

- **2026-10-29** Phase 3 decision: forecasting does **not** add value (S3 vs S1 Sharpe −0.35,
  P = 0.56). Phase 4 benchmark = S1 passive BTC+ETH. S3-EWMA scored best (Sharpe 2.34) but is a
  robustness variant and is not substituted after the fact; its deflated Sharpe over 6 trials is 90%.
  A deflated Sharpe column for every strategy was added after the first run (reporting only).
- **2026-10-29** Engine design choices made while building Phase 3 (before results): positions sized
  by fixed slots (equity / 1.5 / k) and not resized while held; a coin liquidated or force-exited at
  *t* cannot be re-entered in the same window; turnover counts the spot leg's notional.

- **2026-10-29** Phase 3 spec fixed after review: NAV $1M (was $10M); margin buffer 50% with no
  cross-margin (was 20%), because measured one-day rises reach +31% for BTC/ETH and +60% at the
  99.9th percentile for other coins; explicit liquidation rule (40% close-based trigger, 2% penalty);
  daily margin top-ups. Top-5 per venue is the primary rule; top-3 and top-10 are sensitivities
  only, counted in the deflated Sharpe. Assumptions are conservative throughout.

- **2026-10-29** Phase 2 decision: M3 (pooled regression) used downstream; it beat the better simple
  model in 4 of 5 years (threshold 4). Noted: M2 (EWMA) ranks coins slightly better in 4 of 5 years,
  so Phase 3 reports M2-based selection as a robustness check. Error diagnostics by funding state and
  listing age were added after the decision and do not affect it.

- **2026-10-29** Investable set excludes coin-windows with |basis| > 20% (decided before any forecast
  was run). Such prints are not tradable basis trades: collapses (LUNA, May 2022: +15,900%) or spot
  and perp no longer tracking the same token (SXP, April 2026: +2,900%). 790 of 862k Binance prints
  exceed 5%; the Phase 2 report lists what the 20% rule removes.
- **2026-10-29** Spot coverage of the universe (Binance): 100% in 2021–23, falling to 93% (2024),
  86% (2025) and 79% (2026) as new coins increasingly list as perps only.

- **2026-10-29** Phase 2 prices: 8-hour bars (close, quote volume) for spot and perp on both venues,
  timestamped at the bar **close** so they line up with funding windows. Bybit has no 8h interval;
  its 8h bars are built from two 4h bars, and windows missing either bar are dropped. Bars still
  forming at download time are dropped.
- **2026-10-29** Spot is looked up under the plain coin name (`PEPEUSDT` for perp `1000PEPEUSDT`).
  No spot listing on a venue means no spot leg there. Perp prices are divided by the contract
  multiplier (1000PEPE → PEPE) before computing basis.
- **2026-10-29** Bybit spot history starts 2021-07-05 (Bybit's spot market launched in 2021); the
  Bybit spot leg cannot exist before then. Both venues' APIs serve delisted spot pairs (checked: SRM).
- **2026-10-29** Basis is computed from perp and spot closes (tradable prices) rather than Binance's
  premium index (a time-averaged quantity), so it is consistent across venues.

- **2026-10-29** Reorganised into `funding/` (library), `research/` (scripts), `docs/`, `reports/<phase>/`.
  Verified by rerunning Phase 1: the report is byte-identical.

- **2026-10-29** Phase 1 NO-GO under the pre-registered rule (3 of 6 years). Pivot to single-venue
  funding carry. A dry run on incomplete Bybit data had also printed NO-GO; the rule was not changed.

- **2026-10-28** Stopped the multi-asset trend+carry project as too generic. Its lessons
  carry over: measure carry against cash, never benchmark against a strawman, fix test
  rules before seeing results, and deflate Sharpe ratios for every variant tried.
- **2026-10-28** OKX dropped (no free history). Full order books replaced by Binance book depth.
- **2026-10-28** Venues: Binance + Bybit USDT perps as the core, 2021 onwards. Hyperliquid
  deferred to a later cross-check: its API rate limits make a full hourly history pull
  take hours.
- **2026-10-28** Universe: each month, the top 30 coins by trailing 30-day Binance perp volume
  among coins listed on both venues, **including later-delisted coins** (both APIs serve them).
  Stablecoins excluded. Symbols are matched by coin (`1000PEPEUSDT` = `PEPE`).
- **2026-10-28** Fees (base tier, no discounts), checked against venue sources: Binance USDT perps
  0.02% maker / 0.05% taker (Binance's own guide quotes 0.018% / 0.045%, i.e. the same tier with
  the 10% BNB discount); Binance spot 0.10% / 0.10% (0.075% with BNB); Bybit USDT perps 0.02% /
  0.055% (Bybit help centre). Bybit spot is 0.10% / 0.10% for main tokens, but some sources quote
  higher rates for other token classes; recheck in Phase 3. Binance's VIP0 perp taker was 0.04% in
  earlier years, so a flat 0.05% slightly overstates 2021–22 costs (conservative).
- **2026-10-28** TradFi perps excluded. By 2026, stock, ETF and commodity perps (gold, crude,
  Sandisk, SK Hynix, SOXL…) took about a third of the top-30 volume slots. A rule removes any coin
  whose Binance perps are all tagged `TRADIFI_PERPETUAL`/`TradFi`; it drops 228 names and keeps
  crypto tickers that clash with a stock (CAT). Tokenised gold (PAXG) is tagged as a crypto token
  and kept. Limitation: delisted TradFi perps can't be classified (they only launched in 2025).
- **2026-10-28** Some early-2021 months have fewer than 30 members: Bybit listed few USDT perps then.
- **2026-10-28** All funding is summed into 8-hour windows (00/08/16 UTC), because venues
  settle some coins every 1h or 4h.
