# Extension B: stock and commodity perps as synthetic financing (2026-10-30)

> **Exploratory, not part of the paper's results.** Kept for reference; excluded on 2026-10-30.

Generated tables: [`reports/extension_b/report.md`](../reports/extension_b/report.md); figure
`reports/figures/6_tradfi_breakeven.png`. Code: [`research/extension_b_tradfi.py`](../research/extension_b_tradfi.py).
Spec (fixed before analysis): [plan](plan.md#extension-b-spec-stock-and-commodity-perps-as-synthetic-financing-fixed-2026-10-30-before-any-analysis).
Descriptive only; no strategy test.

**Early data.** Most TradFi perps listed around mid-2026: median history 112 days (ETFs) to 141 days
(single stocks). Annualised figures are early estimates.

## What was measured

For each perp, the **implied financing rate** is the annualised funding a long pays. The **break-even
spread** s\* = funding − SOFR − annualised change in the perp's basis to its underlying. A long holder
prefers the perp to stock financed at SOFR + s whenever s > s\*; an arbitrageur (long stock, short perp)
earns carry whenever their financing spread is below s\*. Reported as a distribution, since prime-broker
and TRS spreads vary by agreement.

Coverage after cleaning: 210 single-stock, 62 ETF and 12 commodity perp listings across Binance and Bybit
(each must track its underlying: median gap ≤ 5%), plus 26 Binance perps without a US underlying
(Asian equities, pre-IPO companies, FX).

## Findings

| Asset type | Perps | Implied financing (median) | SOFR | Break-even s\* median (IQR) | Perp cheaper than SOFR financing | Funding prints exactly 0 |
|---|---|---|---|---|---|---|
| ETFs | 62 | **0.1%** | 3.7% | **−2.6%** (−5.3 to +2.2) | 63% of perps | 77% |
| Single stocks | 210 | 3.4% | 3.7% | +1.0% (−3.3 to +5.0) | 41% | 79% |
| Commodities | 12 | 10.0% | 3.7% | +6.0% (−19.4 to +13.8) | 33% | 47% |
| No US underlying | 26 | 10.4% | 3.8% | funding − SOFR +6.6% | — | — |

1. **Synthetic equity leverage is priced at or below SOFR, by exchange design.** Binance sets the
   interest component of the funding formula to **0%** for its stock perps (announced per contract, e.g.
   INTC and HOOD from 2026-02-03), against 0.01% per 8h for crypto perps. With interest at zero,
   funding = premium + clamp(0 − premium, ±0.05%) is **exactly zero** whenever the perp's premium is within
   ±0.05% per 8h: 77–79% of windows for stocks and ETFs. (Bybit's zero share is similar; its parameters
   were not checked.) Since mature listings (July 2026 onwards, 248–284 perps), funding minus SOFR has
   settled at about **−2% to −3% a year** for stocks and ETFs.
2. **Why it is not SOFR + a spread.** That is the price a *lender* charges (a dealer funding a TRS or a
   prime-broker long at SOFR). A perp has no lender: longs and shorts both post margin and funding is
   only a balancing payment set by the exchange's formula. **Why the gap to SOFR persists:** closing it
   needs someone who earns SOFR on cash and can short the stock, while the traders on these venues hold
   USDT collateral that earns nothing, so for them zero-cost leverage is not cheap. Limits to
   arbitrage again, here from access rather than from transfer frictions.
3. **Who could arbitrage it:** someone long the perp and short the stock earns roughly SOFR minus their
   stock-borrow spread, minus the (near-zero) funding: a few percent a year for easy-to-borrow names.
   The friction is access, since it needs both a crypto venue account and a stock-loan desk.
4. **Weekends:** with the underlying market closed, single-stock funding falls from 4.4% to 1.0% a year
   (ETFs 0.5% → 0.0%), while commodities rise (9.6% → 11.6%). Paired across all perps, weekend minus
   weekday is −2.25 points (Wilcoxon p < 0.001).
5. **These markets are less integrated than crypto majors.** Binance–Bybit funding correlation is 0.59 for
   TradFi perps vs 0.69 for crypto majors over the same period, and the 90th-percentile gap is about four
   times larger (3.1 vs 0.8 bp per 8h); gaps decay at a similar speed (half-life about 4 hours).
6. **Commodities and pre-IPO perps price leverage higher:** commodity funding about 10% a year (with a
   noisy basis, since the underlying is a rolling front-month future), and perps without a US
   underlying (including pre-IPO companies) about 6.6% over SOFR.

## Cleaning rules (added after a first look, logged in decisions)

- A coin's funding counts only from its Binance TradFi listing; earlier Bybit history under the same
  name is a different (crypto) instrument (e.g. the GME meme coin, CAT, PENG).
- Perps without a US underlying use Binance only (their instrument cannot be verified on Bybit).
- Basis windows beyond ±20% are dropped: Yahoo back-adjusts history for stock splits (KORU, CRWD)
  while perp prices are not adjusted. The basis drift is a regression slope, not first-vs-last.

## Limitations

A few months of history; underlying prices only at the US close (perp closes at 00:00 UTC, a few hours
after); commodity underlyings are front-month futures that roll; three tickers had no Yahoo data.
