# Phase 1: data and descriptives (completed 2026-10-29)

Generated tables: [`reports/phase1/report.md`](../reports/phase1/report.md).
Code: [`research/phase1_descriptives.py`](../research/phase1_descriptives.py).
Go/no-go rule: [plan](plan.md#phase-1-gono-go-rule-fixed-2026-10-28-before-any-data-was-pulled).

Data: 274 coins (including later-delisted), Binance + Bybit, 2021-01 to 2026-10, 172k coin-periods
with both venues; under 0.5% of in-universe windows missing on either venue.

**Go/no-go: NO-GO.** The top quintile of trailing cross-venue gaps collected **25.0 bp** over 7 days,
above the 21 bp taker round trip on average, but only in **3 of 6 years** (2021, 2023, 2024; 2025
missed by 0.7 bp; 2026 collected 9.8 bp). Only 41% of top-quintile trades beat the cost. At maker
fees (8 bp) every year would pass. That is a sensitivity, not the decision rule.

Findings:
- **Venues are tightly integrated.** Binance–Bybit funding correlation went from 0.71 (2021) to 0.95
  (2023+). The median |gap| is 0.2–0.7 bp per 8h, and gaps mean-revert with a half-life of about
  4.5 hours. This supports the limits-to-arbitrage view: gaps live inside the cost band.
- **The floor dominates.** The median coin's funding is *exactly* the 0.01% floor (10.95% a year) in
  2021, 2023 and 2024; 25–60% of prints sit on it. In 2026 BTC/ETH sit on it only ~6% of the time
  (mostly below it).
- **Alt funding has turned negative and fat-tailed.** The equal-weighted universe paid shorts −12%
  (2025) and −28% (2026) a year, driven by squeezes on newly listed coins (worst: LAB −13.6% in
  one 8-hour window). 29–33% of prints were negative in 2025–26.
- **Carry vs cash by regime (universe median coin):** 2021 +10.9%, 2022 +0.8%, 2023 +5.7%,
  2024 +5.8%, 2025 +2.5%, 2026 +1.0% (median funding minus T-bill, approximate). BTC was strongest
  in 2021 (30.6%) and 2024 (11.9%).
- **Venues changed settlement frequency.** Binance went from 100% 8-hourly (2021) to 41% 4-hourly
  (2026); Bybit followed in 2025.

Implications for the pivot: single-venue carry is attractive only in some regimes and coins, so
choosing *which coins and when* (and staying out) is where an allocator can add value. Alt carry in
2025–26 was negative for the short-perp side; the reverse trade (short spot, long perp) needs spot
borrowing and is a possible extension.
