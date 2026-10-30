# Phase 3: funding-carry backtest (completed 2026-10-29)

Generated tables: [`reports/phase3/report.md`](../reports/phase3/report.md).
Code: [`funding/backtest.py`](../funding/backtest.py), [`funding/metrics.py`](../funding/metrics.py),
[`research/phase3_backtest.py`](../research/phase3_backtest.py).
Spec and decision rule (fixed before any backtest was run): [plan](plan.md#phase-3-spec-backtest-engine-fixed-2026-10-29-before-any-backtest-was-run).

Setup: $1M NAV split across Binance and Bybit, 2022-01 to 2026-10, long spot / short perp, all
returns in excess of T-bills, conservative costs and margin (taker fees, 2 bp slippage per leg,
50% margin buffer with no cross-margin, explicit liquidations).

## Decision

**Forecasting does not add value under the pre-registered rule.** The primary strategy (S3,
cost-aware top-5 using the M3 forecast) had a *lower* Sharpe than passive BTC+ETH (0.83 vs 1.10;
P(S3 not better) = 0.51, needed < 0.10), though it was positive in 3 of 5 years. **Phase 4's
benchmark is S1, passive BTC+ETH.**

## Results

| Strategy | Excess return % a year | Sharpe | Max drawdown | Deflated Sharpe |
|---|---|---|---|---|
| S1 passive BTC+ETH | 0.36 | 1.10 | −2.5% | 13% |
| S2 naive top-5 (weekly rotation) | **−4.31** | −1.68 | −19.0% | 0% |
| **S3 cost-aware top-5 (primary)** | 1.46 | 0.83 | −3.5% | 8% |
| S3-EWMA (robustness) | 2.56 | 1.35 | −2.3% | 37% |
| S3 top-3 / top-10 (sensitivity) | 1.50 / 1.36 | 0.52 / 1.42 | −5.8% / −1.8% | 2% / 44% |

*Corrected 2026-10-29: a bug (entering a coin with a spot price but no perp price that window) made
S3-EWMA's Bybit book undefined from Feb 2025, silently dropping ~20 months. The first version reported
S3-EWMA at Sharpe 2.34 and deflated Sharpe 90%; the corrected figures are above. Other strategies were
unaffected; deflated Sharpes moved because the set of trial Sharpes changed. The decision is unchanged.*

*Second correction, 2026-10-29: charts showed positions in delisted coins (MATIC after its rename to
POL, BNX) held forever with no prices, tying up capital. Held coins with no price for 3 days are now
closed at their last prices with full costs. This raised every strategy that held smaller coins
(S3 1.16% → 1.46%, Sharpe 0.66 → 0.83); passive BTC+ETH is unchanged and so is the decision.*

Passive BTC+ETH in 2021 (context, before forecasts exist): +12.6% excess, Sharpe 10.9.

## What the numbers say

1. **The carry barely beats cash after 2021.** Passive BTC+ETH collected 3.8% of NAV a year in
   funding, but paid away 3.5% in forgone T-bill interest on the capital it ties up (1.5× notional).
   That left +0.36% a year. The trade's 2021 economics (+12.6%) did not survive higher rates and
   compressed funding.
2. **Naive rotation is destroyed by costs.** Weekly top-5 rotation collected the most funding (5.8%)
   but turned over 31× NAV a year: 6.0% in costs plus 0.6% in liquidation penalties. This is the
   Phase 2 warning made concrete.
3. **Cost awareness fixes most of that, but the hurdle is too strict.** S3 cut turnover to 3× and
   costs to 0.6%, but held only **1.7 positions on average out of 10 slots**. The entry rule amortises
   the 0.38% round trip over 7 days, which requires forecast funding of about 24% a year, while held
   positions actually last much longer. That inconsistency (entry priced as a 7-day trade, exit
   allowing indefinite holds) leaves most capital in cash.
4. **The EWMA forecast does somewhat better than M3 in the backtest** (Sharpe 1.35 vs 0.83), as
   Phase 2's ranking results suggested. It is a robustness variant, so it cannot replace the primary
   after the fact, and its deflated Sharpe (37%) is far from the usual 95% once all six variants are
   counted. No variant is statistically distinguishable from luck after deflation.
5. **Small coins bring liquidation risk.** S3 had 7 liquidations and S2 had 14; BTC+ETH had none,
   consistent with Phase 3's measured price spikes.
6. **Capacity is not the constraint at these sizes.** The liquidity cap shrinks positions as NAV
   grows (excess 1.5% at $1M, 1.2% at $10M, 0.3% at $100M), but the number of positions does not
   change.

## Implications for Phase 4 (MILP allocator)

- **The benchmark to beat is passive BTC+ETH:** Sharpe 1.10, +0.36% a year excess.
- **The main opportunity is the entry hurdle, not the forecast.** An optimiser that prices a position
  by its *expected holding period* rather than a fixed 7 days, with open/close binaries carrying the
  real cost, is the natural fix for S3's idle capital.
- **Capital efficiency matters most of all.** The 3.5% a year T-bill drag on tied-up capital is the
  largest cost in every strategy. Cross-margining (spot counted as collateral) would cut it sharply;
  Phase 4 should report results with and without it, since this backtest assumed the worst case.
- Per-coin caps for young and volatile coins are a better tool than more forecast complexity:
  liquidations come from them.

## Why did the carry compress? (discussion, 2026-10-29)

Regimes in the data (Phases 1–2):

| Year | Context | BTC funding % a year | Median coin funding | T-bill | % prints negative | Median basis (bp) | BTC+ETH at floor |
|---|---|---|---|---|---|---|---|
| 2021 | Bull market, retail leverage | 30.6 | 10.95 | 0.05 | 8% | +3.3 | 50% |
| 2022 | LUNA, 3AC/Celsius, FTX: deleveraging | 4.2 | 2.9 | 2.1 | 42% | −6.1 | 28% |
| 2023 | Recovery; policy rate ~5% | 7.9 | 10.95 | 5.3 | 19% | −3.7 | 38% |
| 2024 | Spot BTC ETFs (Jan), rally | 11.9 | 10.95 | 5.2 | 13% | −1.9 | 41% |
| 2025 | Weaker leverage demand; small-coin squeezes | 5.1 | 6.75 | 4.2 | 29% | −4.9 | 18% |
| 2026 (to Oct) | BTC mostly below the floor | 3.1 | 4.8 | 3.8 | 33% | −5.7 | 6% |

Drivers. The first two and the last two are measured in this project's data; the third is a hypothesis
consistent with the timing, not tested here.

1. **The floor is fixed by the exchange, not by interest rates (measured).** 0.01% per 8 hours is
   10.95% a year regardless of the T-bill. Excess at the floor fell from about 10.9% (2021) to about 6%
   on notional once T-bills reached 5%, and to about 2.5% on capital with a 50% margin buffer.
2. **Leverage demand is cyclical (measured).** Funding is the price of leverage: 30.6% for BTC in 2021,
   negative 42% of the time in 2022's deleveraging, a partial revival in 2024.
3. **More arbitrage capital on the short side (hypothesis).** Spot ETFs (2024) industrialised the
   long-spot/short-futures trade; Ethena's USDe (2024) shorts perps at scale to stay delta-neutral;
   more market makers and portfolio-margin tools lower the cost of running the trade. Testable later
   against USDe supply and ETF flows; not pursued in this project.
4. **Persistently negative basis since 2022 (measured).** The perp trades below spot, so short demand
   outweighs leveraged long demand. This is consistent with (3).
5. **Venue changes (measured).** More perp-only listings (spot coverage of the top 30 fell to 72–78%),
   squeeze-driven negative funding in small coins, and faster settlement (4h and 1h).

**Snapshot, 2026-10-29 14:12 UTC (live from both venues; T-bill 4.22%).** The majors sit at or just
below the floor with a slightly negative basis: BTC funding 10.95% a year on Binance and 5.8% on Bybit;
basis −2 to −4 bp. At the floor, BTC carry is about **6.7% a year over cash on notional**, but only about
**3.1% on capital** with the conservative 50% margin buffer, before costs. Today the swing factor is
capital efficiency (cross-margining), not funding. The Binance–Bybit gap (~0.5 bp per 8 hours for BTC)
sits well inside the ~21 bp cost band, as in Phase 1.
