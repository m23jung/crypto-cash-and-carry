"""Sensitivity of funding carry to capital structure (margin, leverage) and to transaction costs.

Not a strategy test: these runs vary assumptions around already-decided strategies and are not
counted as trials. Run:  python research/sensitivity.py   (writes reports/sensitivity/report.md; ~15 min)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
from phase3_backtest import COSTS, NAV, START, STRATEGIES
from phase4_allocator import milp_backtest

from funding import metrics
from funding.backtest import Book, Costs, run
from funding.dataset import VENUES, investable_rows, load, tbill_8h
from funding.forecast import walk_forward
from funding.milp import Params

OUT = Path("reports/sensitivity/report.md")
COINS = ("BTC", "ETH")
BAND = 0.05  # rebalance a position only when it is more than 5% off target


def scaled(c: Costs, k: float) -> Costs:
    return dataclasses.replace(c, spot_fee=c.spot_fee * k, perp_fee=c.perp_fee * k, slippage=c.slippage * k)


def stats(led: pd.DataFrame) -> dict:
    r = led["pnl"] / led["equity_start"] - led["tbill"]
    r = r.groupby(r.index.floor("D")).sum()
    years = len(r) / 365
    return {"excess % a year": r.mean() * 365 * 100, "Sharpe": metrics.sharpe(r),
            "max drawdown %": metrics.max_drawdown(r) * 100, "worst 30 days %": r.rolling(30).sum().min() * 100,
            "funding % NAV a year": (led["funding"] / led["equity_start"]).sum() / years * 100,
            "costs % NAV a year": (led["costs"] / led["equity_start"]).sum() / years * 100,
            "cash − T-bill % NAV a year": ((led["cash"] / led["equity_start"]) - led["tbill"]).sum() / years * 100}


def combine(books: list[pd.DataFrame]) -> pd.DataFrame:
    cols = ["equity_start", "pnl", "funding", "costs", "cash"]
    return sum(b[cols] for b in books).assign(tbill=books[0]["tbill"])


def passive_constant(panels, tbill, margin: float, leverage: float = 1.0, k: float = 1.0,
                     borrow: float | None = None) -> pd.DataFrame:
    """BTC+ETH carry held at notional = leverage x equity / margin, rebalanced weekly with a 5% band.
    Capital tied up per $1 notional = margin; anything beyond equity is borrowed at ``borrow``."""
    books = []
    for v in VENUES:
        costs = dataclasses.replace(scaled(COSTS[v], k), margin_buffer=margin - 1, borrow_rate=borrow)
        b, target, rows = Book(panels[v], NAV / len(VENUES), costs), None, []
        for t in panels[v]["funding"].loc[START:].index:
            b.begin(t, tbill.get(t, 0.0))
            if target is not None:
                adj = {c: x for c, x in target.items() if c not in b.q or abs(b.notional(c) / x - 1) > BAND}
                b.execute_notional({**{c: b.notional(c) for c in b.q}, **adj}, borrow=leverage > 1)
                target = None
            rows.append(b.finish(tbill.get(t, 0.0)))
            if (t.dayofweek == 0 and t.hour == 0) or not b.q:
                target = {c: b.equity * leverage / margin / len(COINS) for c in COINS if c in b.inv}
        books.append(pd.DataFrame(rows).set_index("ts"))
    return combine(books)


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    tb_avg = tbill.loc[START:].mean() * 3 * 365
    out = ["# Sensitivity: capital structure and transaction costs\n\n"
           f"{START[:4]}-01 to {tbill.index[-1]:%Y-%m}, $1M NAV across Binance and Bybit, all returns in excess "
           f"of the T-bill (average {tb_avg * 100:.2f}%). Not strategy tests: assumptions varied around decided "
           "strategies, so these runs are not counted as trials.\n"]

    def section(title, df, note=""):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=".2f") + "\n")

    # A. Margin factor: capital tied up per $1 of notional (unlevered).
    a = {f"{m:.2f}": stats(passive_constant(panels, tbill, m)) for m in [1.0, 1.05, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0]}
    section("A. Margin factor (passive BTC+ETH, constant exposure, unlevered)", pd.DataFrame(a).T.rename_axis("margin"),
            "Margin factor = capital tied up per $1 of notional. 1.0-1.05 matches portfolio/unified margin with spot "
            "counted at a 95% collateral ratio; 1.5 is separate accounts with a 50% buffer.")

    # B. Leverage: notional above equity, borrowed at a given rate (realistic margin 1.05).
    rows = {}
    borrows = [("T-bill + 1% (institutional / repo-like)", tb_avg + 0.01), ("11% (exchange USDT loan)", 0.11)]
    for label, borrow in borrows:
        for lev in [1.0, 1.5, 2.0, 3.0]:
            rows[(label, f"{lev:.1f}x")] = stats(passive_constant(panels, tbill, 1.05, lev, borrow=borrow))
    section("B. Leverage on the spot leg (margin factor 1.05)",
            pd.DataFrame(rows).T.rename_axis(["borrow rate", "leverage"]),
            "Notional = leverage × equity / 1.05; the part above equity is borrowed at the stated annual rate "
            "(held constant, a simplification: exchange borrow rates rise when funding rises).")

    # C. Transaction costs: all fees and slippage scaled by k (1 = conservative base case, ~0.38% round trip).
    print("forecasts", flush=True)
    rows_ = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc7, fc30 = walk_forward(rows_), walk_forward(rows_, target="target_30d")
    c_rows = {}
    for k in [0.0, 0.25, 0.5, 1.0, 1.5, 2.0]:
        c_rows[(f"{k:.2f}", "Passive BTC+ETH (margin 1.10)")] = stats(passive_constant(panels, tbill, 1.10, k=k))
        factory, model, slots = STRATEGIES["S3 cost-aware top-5"]
        books = [run(panels[v], fc7[model].xs(v, level="venue"), factory(scaled(COSTS[v], k)), slots, NAV / 2, tbill,
                     scaled(COSTS[v], k), START) for v in VENUES]
        c_rows[(f"{k:.2f}", "S3 cost-aware top-5 (margin 1.50)")] = stats(combine(books))
        if k in (0.25, 0.5, 1.0, 2.0):
            print(f"MILP k={k}", flush=True)
            costs = {v: scaled(COSTS[v], k) for v in VENUES}
            led = milp_backtest(panels, fc30["M3_regression"], tbill, Params(), costs=costs)
            c_rows[(f"{k:.2f}", "MILP primary (margin 1.50)")] = stats(led)
    section("C. Transaction costs (fees + slippage × k)",
            pd.DataFrame(c_rows).T.rename_axis(["cost multiplier", "strategy"]).sort_index(level=[1, 0]),
            "k = 1 is the conservative base case (taker fees, 2 bp slippage per leg, ~0.38% round trip); "
            "k = 0.5 is roughly maker execution or a VIP fee tier; k = 0 isolates gross carry.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
