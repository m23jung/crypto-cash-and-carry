"""Phase 3: backtest of spot/perp funding-carry strategies. Spec: docs/plan.md, "Phase 3 spec".

Run after research/build_data.py:  python research/phase3_backtest.py   (writes reports/phase3/report.md)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from funding import metrics
from funding.backtest import Costs, cost_aware_top_k, naive_top_k, passive, run
from funding.dataset import VENUES, investable_rows, load, tbill_8h
from funding.forecast import walk_forward

NAV = 1_000_000
START, YEARS = "2022-01-01", range(2022, 2027)
COSTS = {"binance": Costs(), "bybit": Costs(perp_fee=0.00055)}
OUT = Path("reports/phase3/report.md")

# name -> (rule factory taking Costs, forecast column, slots per venue). Every entry counts as a trial.
STRATEGIES = {
    "S1 passive BTC+ETH": (lambda c: passive(("BTC", "ETH")), None, 2),
    "S2 naive top-5": (lambda c: naive_top_k(5), "M3_regression", 5),
    "S3 cost-aware top-5": (lambda c: cost_aware_top_k(5, c), "M3_regression", 5),
    "S3-EWMA top-5": (lambda c: cost_aware_top_k(5, c), "M2_ewma", 5),
    "S3 top-3 (sensitivity)": (lambda c: cost_aware_top_k(3, c), "M3_regression", 3),
    "S3 top-10 (sensitivity)": (lambda c: cost_aware_top_k(10, c), "M3_regression", 10),
}
PRIMARY, BASELINE = "S3 cost-aware top-5", "S1 passive BTC+ETH"
COMPONENTS = ["funding", "basis", "unhedged", "costs", "liquidation", "cash", "traded"]


def backtest(panels, forecasts, tbill, name, nav=NAV, start=START) -> pd.DataFrame:
    """Both venues, NAV split 50/50; returns the combined per-window ledger."""
    factory, model, slots = STRATEGIES[name]
    books = []
    for v in VENUES:
        fc = forecasts[model].xs(v, level="venue") if model else pd.Series(dtype=float)
        books.append(run(panels[v], fc, factory(COSTS[v]), slots, nav / len(VENUES), tbill, COSTS[v], start))
    return sum(b[["equity_start", "pnl", "n_held", "liquidations", *COMPONENTS]] for b in books).assign(
        tbill=books[0]["tbill"])


def daily_excess(ledger: pd.DataFrame) -> pd.Series:
    r = ledger["pnl"] / ledger["equity_start"] - ledger["tbill"]
    return r.groupby(r.index.floor("D")).sum()


def summary(ledger: pd.DataFrame) -> dict:
    r = daily_excess(ledger)
    years = len(r) / metrics.DAYS
    weekly = r.groupby(r.index.to_period("W")).sum()
    nav = ledger["equity_start"]
    return {
        "excess return % a year": r.mean() * metrics.DAYS * 100,
        "volatility % a year": r.std() * metrics.DAYS**0.5 * 100,
        "Sharpe": metrics.sharpe(r),
        "max drawdown %": metrics.max_drawdown(r) * 100,
        "worst week %": weekly.min() * 100,
        "turnover x NAV a year": ledger["traded"].sum() / nav.mean() / years,
        "cost drag % a year": (ledger["costs"] / nav).sum() / years * 100,
        "liquidations": int(ledger["liquidations"].sum()),
        "avg positions": ledger["n_held"].mean(),
        "PSR": metrics.probabilistic_sharpe(r),
    }


def attribution(ledger: pd.DataFrame) -> pd.Series:
    """Annualised % of NAV; sums to the excess return over T-bills."""
    nav, years = ledger["equity_start"], len(ledger) / (3 * 365)
    parts = {k: (ledger[k] / nav).sum() / years * 100 for k in ["funding", "basis", "unhedged"]}
    parts["costs"] = -(ledger["costs"] / nav).sum() / years * 100
    parts["liquidation"] = -(ledger["liquidation"] / nav).sum() / years * 100
    parts["cash minus T-bill on NAV"] = ((ledger["cash"] / nav) - ledger["tbill"]).sum() / years * 100
    parts["total excess"] = sum(parts.values())
    return pd.Series(parts)


def main():
    panels = load()
    index = panels["binance"]["funding"].index
    tbill = tbill_8h(index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    forecasts = walk_forward(rows)

    ledgers = {name: backtest(panels, forecasts, tbill, name) for name in STRATEGIES}
    rets = {name: daily_excess(ledger) for name, ledger in ledgers.items()}
    trials = [metrics.sharpe(r) for r in rets.values()]

    out = ["# Phase 3: funding-carry backtest\n\n"
           f"NAV ${NAV:,.0f} split 50/50 across Binance and Bybit, {START[:4]}-01 to {index[-1]:%Y-%m}. "
           "Conservative assumptions (taker fees, 2 bp slippage per leg, 50% margin buffer with no "
           "cross-margin, explicit liquidations). Spec: [docs/plan.md](../../docs/plan.md). "
           "All returns are in excess of the 3-month T-bill.\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=fmt) + "\n")

    table = pd.DataFrame({n: summary(ld) for n, ld in ledgers.items()}).T
    table["deflated Sharpe"] = [metrics.deflated_sharpe(rets[n], trials) for n in table.index]
    section("1. Summary (full period)", table, "PSR = probability the Sharpe is above zero; deflated Sharpe also "
            f"accounts for all {len(STRATEGIES)} strategies run.")
    by_year = pd.DataFrame({n: r.groupby(r.index.year).sum() * 100 for n, r in rets.items()}).T
    section("2. Excess return by year (%)", by_year, "2026 is a partial year.")
    section("3. P&L attribution (% of NAV a year)", pd.DataFrame({n: attribution(ld) for n, ld in ledgers.items()}).T,
            "Funding received, basis change, unhedged spot after liquidations, trading costs, liquidation "
            "penalties, and idle cash interest minus the T-bill on the whole NAV. Sums to the excess return.")

    # Decision (pre-registered).
    diff, (lo, hi), p = metrics.paired_sharpe_test(rets[PRIMARY], rets[BASELINE])
    positive_years = int((by_year.loc[PRIMARY, list(YEARS)] > 0).sum())
    adds_value = p < 0.10 and positive_years >= 3
    benchmark = max([PRIMARY, BASELINE], key=lambda n: metrics.sharpe(rets[n]))
    dsr = metrics.deflated_sharpe(rets[PRIMARY], trials)
    out.append(
        f"\n## 4. Decision (rule fixed in advance)\n\n"
        f"- Sharpe difference {PRIMARY} − {BASELINE}: **{diff:+.2f}** (95% interval {lo:+.2f} to {hi:+.2f}); "
        f"P(difference ≤ 0) = **{p:.2f}** (need < 0.10).\n"
        f"- {PRIMARY} positive in **{positive_years} of {len(YEARS)}** years (need 3).\n"
        f"- **Forecasting adds value: {'YES' if adds_value else 'NO'}.**\n"
        f"- Deflated Sharpe of {PRIMARY} over {len(trials)} trials: **{dsr:.0%}** "
        f"(probability its Sharpe is real after counting every variant).\n"
        f"- **Phase 4 benchmark: {benchmark}** (better full-period Sharpe of the two).\n")
    if all(by_year.loc[n].sum() <= 0 for n in STRATEGIES):
        out.append("- Every strategy's excess return is ≤ 0 after costs: funding carry did not beat T-bills "
                   "in this period.\n")

    # Capacity (not counted as trials: same rule, different size).
    cap = pd.DataFrame({f"${n / 1e6:.0f}M": summary(backtest(panels, forecasts, tbill, PRIMARY, nav=n))
                        for n in (1e6, 1e7, 1e8)}).T[["excess return % a year", "Sharpe", "avg positions",
                                                      "cost drag % a year"]]
    section(f"5. Capacity: {PRIMARY} at larger sizes", cap,
            "The 1%-of-daily-volume cap binds as size grows; unfilled slots stay in cash.")

    s1_2021 = backtest(panels, forecasts, tbill, BASELINE, start="2021-01-08")
    r21 = daily_excess(s1_2021).loc["2021"]
    out.append(f"\n## 6. Context: {BASELINE} in 2021 (before forecasts exist)\n\n"
               f"Excess return {r21.sum() * 100:.1f}%, Sharpe {metrics.sharpe(r21):.2f}, "
               f"max drawdown {metrics.max_drawdown(r21) * 100:.1f}%.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
