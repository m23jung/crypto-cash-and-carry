# Phase 2: investable set, basis and funding forecasts (completed 2026-10-29)

Generated tables: [`reports/phase2/report.md`](../reports/phase2/report.md).
Code: [`research/phase2_forecast.py`](../research/phase2_forecast.py), [`funding/forecast.py`](../funding/forecast.py).
Spec and decision rule (fixed before any forecast was run): [plan](plan.md#phase-2-spec-funding-forecasts-fixed-2026-10-29-before-any-forecast-was-run).

## Decision

**M3 (pooled regression) goes into the allocator.** It beat the better of last value and EWMA on
out-of-sample error in **4 of 5 years**, exactly the threshold. It lost in 2023 (0.94 vs 0.89 bp per 8h).

## Investable set

- A coin is investable when it is in the top 30, has spot on the same venue, and its basis is under 20%.
- **About 25 coins per venue** from 2022. Bybit had about 6 in 2021 because its spot market only
  opened in July 2021.
- **Spot coverage is shrinking:** Binance 100% (2021–23) → 78% (2026); Bybit 90% (2024) → 72% (2026).
  New coins increasingly list as perps only, so the basis trade's opportunity set is narrowing.
- The 20% basis rule removed only 24 windows (VANRY, ALPACA, LUNA, BNX, plus one-off prints).

## Basis

- The **median perp has traded below spot since 2022**: −2 to −6 bp; +2 to +3 bp in 2021.
- So a long-spot/short-perp position usually *enters at a discount*. Convergence helps it, but the
  discount also signals weak leverage demand, which goes with lower funding.
- Bybit's tails are wider than Binance's (2021 5th percentile −47 bp vs −10 bp): thinner spot books.

## Forecasts (out of sample, 2022–2026)

| | Error (MAE) | Ranking (rank IC) | Top fifth vs all (% a year) |
|---|---|---|---|
| M0 floor | worst overall | n/a | n/a |
| M1 last value | beaten by M2 every year | 0.37–0.60 | 4.6–10.5 |
| M2 EWMA (1–3 day half-life) | best simple model | **best in 4 of 5 years** (0.49–0.70) | 6.5–15.2 |
| M3 regression | **best in 4 of 5 years** | 0.47–0.68 | 6.3–16.8 |

- **M3 wins on level, M2 on ranking.** M3's error advantage comes almost entirely from **negative-
  funding states** (MAE 1.63 vs 2.16 bp), where it predicts recovery toward the floor better.
  **At the floor, M3 is the worst model** (0.64 vs EWMA 0.56 and the constant floor 0.61): there it
  adds noise. Above the floor, EWMA is better (1.47 vs 1.58).
- **Young coins are hardest.** Coins listed under 90 days have about twice the error of older coins.
  M3 handles them best (1.70 vs 2.03).
- **Ranking is strong.** A rank IC around 0.5 is very high by equity-factor standards. Funding is
  persistent across coins even though individual prints mean-revert within a day.
- **Economic value is large but must be weighed against turnover.** The top fifth by forecast earned
  6–17% a year more than the average investable coin (before costs). A full weekly rotation at
  ~30 bp round trip costs about 15.6% a year, roughly the size of the gain. So the allocator's job is
  to **rotate only when the forecast gap clears the cost**, which is the MILP's open/close binaries.

## Implications for Phases 3–4

1. The allocator uses M3 for levels (does a coin clear the cost and T-bill hurdle?). Phase 3
   should also report M2-based selection as a robustness check, since M2 ranks slightly better.
2. Turnover control matters as much as the forecast: fixed open/close costs and a minimum
   holding period belong in the backtest and the MILP.
3. Young coins and negative-funding states are where forecasts are least reliable and the tail
   risk is largest; candidates for position caps rather than more model complexity.
4. A more complex forecast (Phase 2b) is not justified yet. The remaining error is concentrated in
   negative states and young coins, so a tail-aware forecast (quantile regression with listing age)
   is the natural candidate *if* Phase 3 shows those states drive losses.
