# Sensitivity: capital structure and transaction costs (2026-10-29)

Generated tables: [`reports/sensitivity/report.md`](../reports/sensitivity/report.md).
Code: [`research/sensitivity.py`](../research/sensitivity.py).

These runs vary assumptions around strategies that were already decided (passive BTC+ETH, S3, the
MILP). They are not strategy tests and are not counted as trials in any deflated Sharpe.
Period 2022-01 to 2026-10, $1M NAV, returns in excess of the T-bill (average 4.12%).

## Is the margin assumption realistic?

Published venue parameters (checked 2026-10-29):
- BTC and ETH count at a **95% collateral ratio** in Binance Portfolio Margin and in Bybit's Unified
  Trading Account (Bybit tiered since July 2025: about 98% for 0–10 BTC, lower for larger holdings).
- BTCUSDT perp **maintenance margin 0.40%** for small positions (about $300k notional).
- Bybit's spot hedging treats BTC spot and BTC perps as **one risk unit**.
- Smaller coins get lower collateral ratios, which venues cut frequently.

So capital tied up per $1 of BTC/ETH carry is **about 1.0–1.05** under portfolio or unified margin (1.10
with a safety buffer). The 1.50 base case of Phases 3–4 (separate accounts, 2× short) is the worst case.
1.30 for smaller coins is plausible but varies widely. Eligibility thresholds could not be confirmed,
and neither venue serves Canadian (Ontario) residents.

## Margin factor (passive BTC+ETH, constant exposure, weekly rebalance with a 5% band)

| Margin factor | 1.00 | 1.05 | 1.10 | 1.20 | 1.30 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|
| Excess % a year | **+1.71** | +1.43 | +1.18 | +0.74 | +0.36 | −0.24 | −1.21 |
| Sharpe | 2.83 | 2.49 | 2.15 | 1.47 | 0.78 | −0.59 | −4.04 |
| Max drawdown | −2.1% | −2.1% | −2.1% | −2.3% | −2.7% | −3.2% | −6.2% |

- **Rule of thumb:** excess ≈ funding ÷ margin factor − T-bill − rebalancing costs. With funding of
  6.4% on notional, T-bills of 4.1% and costs of about 0.5%, **break-even is a margin factor of about 1.4.**
- Each +0.1 of margin factor costs about 0.4–0.5% a year. A higher factor shrinks good years (2024:
  +6.9% at 1.0, +0.8% at 2.0) and deepens bad ones; drawdowns grow while volatility falls.
- In years when funding is below T-bills even on notional (2026 to date), no margin arrangement helps.
- The never-rebalanced passive strategy of Phase 3 looked better at 1.5 (+0.36%) only because its
  exposure drifted favourably with prices (56% of capital deployed in 2022, 124% in 2025).

## Leverage on the spot leg (margin factor 1.05, borrowed part at a constant rate)

| Leverage | 1.0× | 1.5× | 2.0× | 3.0× |
|---|---|---|---|---|
| Borrow at T-bill + 1%: excess / Sharpe / max DD | +1.41 / 2.45 / −2.1% | +1.65 / 1.90 / −3.4% | +1.86 / 1.61 / −5.2% | +2.28 / 1.31 / −8.5% |
| Borrow at 11% (exchange USDT loan): excess / Sharpe / max DD | +1.28 / 2.23 / −2.2% | −1.31 / −1.52 / −8.2% | −4.05 / −3.51 / −17.8% | −9.55 / −5.52 / −36.8% |

- Leverage pays only when funding exceeds the borrow rate plus costs. At cost-of-cash financing each
  extra 1× adds about 0.4% a year but roughly doubles the drawdown; at exchange loan rates it destroys
  the trade. Holding the borrow rate constant flatters leverage, because exchange borrow rates rise
  when funding rises (both are driven by demand for leverage).
- Routes and their financing cost: exchange margin loans (dynamic; about 0.03% a day, ≈ 11% a year, in
  late 2025); institutional crypto lending (negotiated, counterparty risk); the traditional route of a
  spot ETF financed at about SOFR plus a spread and hedged with CME futures (the institutional basis
  trade); on-chain lending (variable, smart-contract risk).
- **Better than leverage: earn on the capital already tied up.** The largest cost in every run is cash
  vs T-bill (about −4.1% of NAV a year). Yield-bearing collateral, where a venue accepts it, attacks
  that directly without adding risk.

## Transaction costs (all fees and slippage × k; k = 1 is the base case, ~0.38% round trip)

| k | 0 | 0.25 | 0.5 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|
| Passive BTC+ETH (margin 1.10) | +1.68 | +1.56 | +1.43 | +1.18 | +0.93 | +0.68 |
| MILP primary (margin 1.50) | | +1.06 (Sharpe 0.96) | +0.82 | +0.67 | | +0.31 |
| S3 cost-aware top-5 (margin 1.50) | +2.05 | +0.88 | +1.05 | +1.46 | +0.86 | +0.77 |

- **Passive is robust:** about −0.27% a year per +0.5 in k, still positive at double costs.
- **The MILP is the most cost-sensitive** (its churn): +1.06% a year at k = 0.25 vs +0.31% at k = 2.
  Even with maker or VIP fees its Sharpe (0.96) stays below the same-margin benchmark (S1, 1.10).
- **S3 gets worse when costs fall** (k = 0.25: +0.88%, drawdown −6.1%): its entry hurdle scales with
  costs, so cheaper costs admit more marginal small coins, with more liquidations and basis losses.
  The cost hurdle was acting as a hidden quality filter; risk controls belong in the rule explicitly.

## Takeaway

The carry is a financing trade. What moves results, in order: the capital structure (margin factor,
yield on collateral), execution costs (mainly for active strategies), and only then coin selection.
