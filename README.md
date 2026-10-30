# Crypto Cash-and-Carry: Capital Efficiency in the Spot–Perpetual Basis Trade

Crypto perpetual futures charge a **funding rate** that works like a repo rate for leverage:
leveraged longs pay whoever supplies balance sheet. Buying spot and shorting the perp collects it
with no price risk. This project measures that carry with free exchange data (Binance, Bybit,
2021–2026, including later-delisted coins) and tests, under pre-registered rules, whether
cross-venue arbitrage, funding forecasts or a mixed-integer allocator (HiGHS) beat simply holding
it. **They don't, after costs: the outcome is decided by capital structure, not selection.**

[![CI](https://github.com/m23jung/crypto-cash-and-carry/actions/workflows/ci.yml/badge.svg)](https://github.com/m23jung/crypto-cash-and-carry/actions/workflows/ci.yml)

**Read the paper: [PDF](docs/paper.pdf) · [web version](docs/paper.md)** · October 2026

![Cumulative excess return](reports/figures/1_cumulative_excess_return.png)

## Key findings

- **Venues are tightly integrated.** Binance–Bybit funding correlation is 0.95 since 2023, and gaps
  halve in about 4.5 hours. Cross-venue gaps mostly sit inside the round-trip cost band.
- **The band widens with frictions.** Against Hyperliquid, an on-chain venue where capital moves by
  bridge, gaps are about twice as wide as Binance–Bybit on the same coins, and their largest gaps
  cleared trading fees 69% of the time (vs 24%), before bridging costs. That band is narrowing.
- **The 0.01% floor dominates.** The median coin pays *exactly* 0.01% per 8h (10.95% a year) in most
  years; excess over T-bills ranged from +10.9% (2021) to about +1% (2026).
- **Small-coin funding has turned negative and fat-tailed** (2025–26): squeezes on new listings
  paid shorts as little as −13.6% in a single 8-hour window.
- **Funding is forecastable across coins.** Out of sample (2022–26), a simple forecast ranks coins with
  rank IC about 0.5; the top fifth earned 6–17% a year more than the average investable coin before
  costs. That gain is about the size of a full weekly rotation's costs, so turnover control matters.
- **The basis trade's opportunity set is shrinking:** spot coverage of top-30 perps fell from 100%
  (2021–23) to 72–78% (2026) as new coins list as perps only.

- **After 2021, carry barely beats cash.** Passive BTC+ETH carry earned +0.36% a year over T-bills
  in 2022–26 (Sharpe 1.0), against +12.6% in 2021. Funding of 3.8% of NAV was mostly offset by the
  T-bill interest forgone on capital tied up.
- **Costs and capital efficiency decide the outcome.** Naive weekly rotation lost 4.5% a year to costs;
  a cost-aware rule kept most capital idle. The largest drag in every strategy is forgone T-bill
  interest on margin and spot capital.

- **Capital efficiency beats optimisation.** Counting spot as collateral took passive BTC+ETH from
  +0.36% to +1.71–1.94% a year. The MILP collected carry but gave much of it back in rotation costs;
  churn controls helped (0.67% → 1.53%) but not enough to beat passive (Sharpe 1.3 vs 4.2).

- **The carry is a financing trade.** Break-even capital per $1 of notional is about 1.4×; realistic
  portfolio margin (about 1.05×) gives passive BTC+ETH about +1.4% a year over T-bills (Sharpe 2.4).
  Leverage only helps at cost-of-cash financing, and mostly adds drawdown.

Details: [Phase 1](docs/phase1.md), [Phase 2](docs/phase2.md), [Phase 3](docs/phase3.md), [Phase 4](docs/phase4.md),
[Phase 4b](docs/phase4b.md), [sensitivity](docs/sensitivity.md).

## Documents

| | |
|---|---|
| [docs/paper.md](docs/paper.md) | **The paper**: question, data, protocol, results, limitations |
| [docs/interview_notes.md](docs/interview_notes.md) | Pitch, key numbers, likely questions and answers |
| [docs/plan.md](docs/plan.md) | Research questions, hypothesis, background, data, phases, go/no-go rule, pivot plan |
| [docs/decisions.md](docs/decisions.md) | Dated log of every analysis decision |
| [docs/phase1.md](docs/phase1.md) | Phase 1 findings and interpretation |
| [docs/phase2.md](docs/phase2.md) | Phase 2 findings and interpretation |
| [docs/phase3.md](docs/phase3.md) | Phase 3 findings and interpretation |
| [docs/phase4.md](docs/phase4.md) | Phase 4 findings and interpretation |
| [docs/phase4b.md](docs/phase4b.md) | Phase 4b: churn controls and realistic margin |
| [docs/sensitivity.md](docs/sensitivity.md) | Margin, leverage and transaction-cost sensitivity |
| [docs/extension_a.md](docs/extension_a.md) | Extension A: on-chain venues and the width of the no-arbitrage band |
| [reports/](reports/) | Generated tables (one folder per phase) |

## Layout

```
funding/        importable library
  sources.py    Binance / Bybit / FRED downloaders
  store.py      SQLite cache
  panels.py     point-in-time universe, 8-hour funding, prices and basis
  dataset.py    venue panels and investable set shared by Phases 2–4
  forecast.py   funding features, models M0–M3, leak-free walk-forward
  backtest.py   8-hour spot/perp carry engine with P&L attribution
  metrics.py    Sharpe, drawdown, probabilistic and deflated Sharpe, paired bootstrap
  milp.py       daily MILP allocator (HiGHS via scipy.optimize.milp)
research/       one runnable script per step
  build_data.py
  phase1_descriptives.py
  phase2_forecast.py
  phase3_backtest.py
  phase4_allocator.py
  phase4b_allocator.py
  sensitivity.py
  build_extensions.py   data for the extensions
  extension_a_onchain.py
  extension_b_tradfi.py   (exploratory, not in the results)
  figures.py
reports/        generated output, by phase
docs/           plan, decisions, phase write-ups
tests/
data/           local cache (gitignored)
```

## Running it

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python research/build_data.py          # ~1.5 h the first time (rate limits); resumable
.venv/bin/python research/phase1_descriptives.py # writes reports/phase1/report.md
.venv/bin/python research/phase2_forecast.py     # writes reports/phase2/report.md
.venv/bin/python research/phase3_backtest.py     # writes reports/phase3/report.md
.venv/bin/python research/phase4_allocator.py    # writes reports/phase4/report.md (~10 min)
.venv/bin/pytest
```
