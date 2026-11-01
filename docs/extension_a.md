# Extension A: does the no-arbitrage band widen with frictions? (2026-10-30)

> **Not part of the paper's results.** Removed on 2026-10-31 when the project narrowed to single-venue
> carry; kept for reference.

Generated tables: [`reports/extension_a/report.md`](../reports/extension_a/report.md).
Code: [`research/extension_a_onchain.py`](../research/extension_a_onchain.py).
Spec (fixed before analysis): [plan](plan.md#extension-a-spec-does-the-no-arbitrage-band-widen-with-frictions-fixed-2026-10-30-before-any-analysis).

## Question

Phase 1 found that Binance–Bybit funding gaps sit inside the cost band. If frictions set the band, gaps
between a centralised venue and an on-chain one, where moving capital means bridging stablecoins and
waiting for chain confirmations, should be wider and slower to close. Each on-chain pair is compared
with Binance–Bybit on the **same coin-windows**, 2023-11 to 2026-10.

## Pre-registered result: the prediction holds

| Pair (vs matched Binance–Bybit) | Years with wider median gap **and** longer half-life |
|---|---|
| Binance–Hyperliquid | 2 of 3 (2025, 2026) |
| Binance–dYdX | 3 of 3 |

Both pairs needed at least 2 of 3. **But only the Hyperliquid comparison is interpretable** (below).

## Binance–Hyperliquid: the clean test

Hyperliquid uses the same funding design as Binance (a 0.01% per 8h floor; median coin exactly on it),
so its gaps are comparable.

| | Binance–Hyperliquid | Binance–Bybit (matched) |
|---|---|---|
| Median \|gap\| (bp per 8h) | **0.62** | 0.32 |
| 90th percentile \|gap\| | **3.40** | 1.63 |
| Funding correlation | 0.85 | 0.91 |
| Gap half-life (hours): 2024 / 2025 / 2026 | 3.4 / **4.6** / **11.2** | 8.6 / 3.6 / 5.4 |
| Top-quintile gap collected over 7 days | **46 bp** | 13 bp |
| Round-trip taker cost | 19 bp | 21 bp |
| Share of top-quintile trades beating the cost | **69%** | 24% |

- **Gaps are about twice as wide** and their tails twice as fat, and in 2025–26 they close more slowly:
  the friction story holds.
- **Unlike Binance–Bybit, the largest on-chain gaps cleared trading costs most of the time** (69% vs
  24%). That is before bridging costs, transfer delays and on-chain risk, which are exactly the frictions
  that keep these gaps open; the costs a trader cannot see in fees.
- **The band is narrowing.** The top-quintile 7-day gap fell from 54 bp (2024) to 20 bp (2025) and 14 bp
  (2026), and the share beating costs from 80% to 25%: arbitrage capital has been moving on-chain.

## Binance–dYdX: confounded by the funding formula

dYdX's funding has **no interest floor and no dead zone** (median 0.00% a year vs 10.95% elsewhere;
7% of windows at 0.01% vs 33–45%). Small premium moves pass straight into dYdX funding while Binance's
clamp holds it flat at the floor, so the two series barely co-move (correlation 0.09) and their gap is
largely mechanical. A robustness check that removes Binance's floor (added after seeing results) leaves
the median gap unchanged at about 1 bp, confirming the gap reflects the formula rather than frictions.
The dYdX "pass" should not be read as evidence about frictions.

## Takeaway

Where funding designs match (Binance vs Hyperliquid), larger transfer frictions come with a wider,
slower-closing band, and its largest gaps exceed trading fees, consistent with limits to arbitrage: the
gaps are paid for by the frictions fees do not capture. The band has been narrowing as capital moves
on-chain. Where designs differ (dYdX), venue mechanics dominate and the comparison says little.

## Limitations

Hourly funding summed into 8-hour windows; no bridging or transfer costs modelled; only three years;
Hyperliquid and dYdX list fewer coins (130 and 115 of the universe).
