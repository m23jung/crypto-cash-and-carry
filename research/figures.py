"""Figures tying the strategies together: returns, P&L sources, cost of capital, MILP positions and trading.

Run:  python research/figures.py   (writes reports/figures/*.png; runs the MILP once, ~3 min)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from phase3_backtest import BASELINE, COSTS, NAV, START, STRATEGIES, attribution, backtest, daily_excess  # noqa: E402

from funding.backtest import run, run_joint  # noqa: E402
from funding.dataset import VENUES, investable_rows, load, tbill_8h  # noqa: E402
from funding.forecast import walk_forward  # noqa: E402
from funding.milp import Params, make_allocator  # noqa: E402

OUT = Path("reports/figures")
# Validated default palette (categorical slots 1-4), chart chrome and diverging poles, light mode.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
POS, NEG = "#2a78d6", "#e34948"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f0efec", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "lines.linewidth": 1.6, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "legend.frameon": False,
})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


def label_line_ends(ax, series: dict[str, pd.Series], colors: dict[str, str], fmt="{:+.1f}%"):
    """Direct labels at each line's last point, nudged apart so they don't collide."""
    ends = sorted(((s.dropna().iloc[-1], name) for name, s in series.items()), reverse=True)
    lo, hi = ax.get_ylim()
    gap, placed = (hi - lo) * 0.06, []
    x = max(s.dropna().index[-1] for s in series.values())
    for y, name in ends:
        y_text = min([y] + [p - gap for p in placed]) if placed and y > placed[-1] - gap else y
        placed.append(y_text)
        ax.annotate(f"{name}  {fmt.format(y)}", (x, y), xytext=(8, (y_text - y) / (hi - lo) * 300),
                    textcoords="offset points", va="center", fontsize=9, color=INK,
                    arrowprops=None)
        ax.plot([x], [y], "o", ms=5, color=colors[name], mec=SURFACE, mew=1.5, zorder=5)


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc7, fc30 = walk_forward(rows), walk_forward(rows, target="target_30d")

    ledgers = {"Passive BTC+ETH": backtest(panels, fc7, tbill, BASELINE),
               "S3 cost-aware top-5": backtest(panels, fc7, tbill, "S3 cost-aware top-5")}
    cross = {v: dataclasses.replace(c, margin_buffer=0.10) for v, c in COSTS.items()}
    books = [run(panels[v], pd.Series(dtype=float), STRATEGIES[BASELINE][0](cross[v]), 2, NAV / 2, tbill, cross[v],
                 START) for v in VENUES]
    cols = ["equity_start", "pnl", "n_held", "liquidations", "funding", "basis", "unhedged", "costs",
            "liquidation", "cash", "traded"]
    ledgers["Passive, cross-margin"] = sum(b[cols] for b in books).assign(tbill=books[0]["tbill"])
    print("running MILP")
    milp = run_joint(panels, make_allocator(fc30["M3_regression"], panels, tbill, Params()), NAV, tbill, COSTS,
                     None, START)
    ledgers["MILP allocator"] = milp
    order = ["Passive, cross-margin", "Passive BTC+ETH", "MILP allocator", "S3 cost-aware top-5"]
    colors = dict(zip(order, SERIES, strict=True))

    # 1. Cumulative excess return.
    fig, ax = plt.subplots(figsize=(10, 5))
    cum = {n: daily_excess(ledgers[n]).cumsum() * 100 for n in order}
    for n in order:
        ax.plot(cum[n].index, cum[n], color=colors[n], label=n)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_title("Cumulative return over T-bills, % of NAV ($1M, both venues, after all costs)")
    ax.set_ylabel("% of NAV")
    ax.margins(x=0.01)
    ax.set_xlim(right=ax.get_xlim()[1] + 230)
    label_line_ends(ax, cum, colors)
    ax.legend(loc="upper left", ncols=2)
    save(fig, "1_cumulative_excess_return.png")

    # 2. Where the P&L comes from (waterfall per strategy, % of NAV a year).
    parts = {"funding": "Fund-\ning", "basis": "Basis", "unhedged": "Un-\nhedged", "costs": "Costs",
             "liquidation": "Liqui-\ndation", "cash minus T-bill on NAV": "Cash −\nT-bill"}
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), sharey=True)
    for ax, n in zip(axes, order, strict=True):
        a = attribution(ledgers[n])
        vals, start = [a[k] for k in parts], 0.0
        for i, v in enumerate(vals):
            ax.bar(i, v, bottom=start, color=POS if v >= 0 else NEG, width=0.72, edgecolor=SURFACE, linewidth=2)
            start += v
        ax.bar(len(vals), a["total excess"], color=INK2, width=0.72, edgecolor=SURFACE, linewidth=2)
        ax.text(len(vals), a["total excess"], f"{a['total excess']:+.2f}%", ha="center",
                va="bottom" if a["total excess"] >= 0 else "top", fontsize=9, fontweight="bold")
        ax.axhline(0, color=AXIS, lw=1)
        ax.set_xticks(range(len(vals) + 1), [*parts.values(), "Total"], fontsize=8)
        ax.set_title(n, fontsize=10.5)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("% of NAV a year")
    fig.suptitle("Where the excess return comes from (blue adds, red subtracts, gray = total)", x=0.06, ha="left",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    save(fig, "2_pnl_attribution.png")

    # 3. Funding vs the cost of capital.
    f = panels["binance"]["funding"]["BTC"].loc["2021":]
    daily = f.groupby(f.index.floor("D")).sum() * 365 * 100
    t_ann = tbill.groupby(tbill.index.floor("D")).sum().loc["2021":] * 365 * 100
    daily, t_ann = daily.iloc[:-1], t_ann.iloc[:-1]  # drop today's partial day
    lines = {"BTC funding (Binance, 30-day avg)": daily.rolling(30).mean(),
             "Capital cost, no cross-margin (1.5 × T-bill)": t_ann * 1.5,
             "Capital cost, cross-margin (1.1 × T-bill)": t_ann * 1.1}
    fig, ax = plt.subplots(figsize=(10, 5))
    for (n, s), c in zip(lines.items(), SERIES, strict=False):
        ax.plot(s.index, s, color=c, label=n, lw=1.6 if "funding" in n else 2)
    ax.axhline(10.95, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(pd.Timestamp("2026-04-01", tz="UTC"), 12.0, "funding floor 10.95%", color=INK2, fontsize=9)
    ax.set_ylim(-15, 45)
    ax.text(daily.index[60], 43, "2021 peaks above 45% clipped", color=MUTED, fontsize=8)
    ax.set_title("The floor stayed fixed while the cost of capital rose: carry = funding minus capital cost")
    ax.set_ylabel("% a year")
    ax.legend(loc="upper right")
    save(fig, "3_funding_vs_capital_cost.png")

    # 4. MILP positions over time.
    pos = milp.attrs["positions"]
    pos["week"] = pos["ts"].dt.tz_localize(None).dt.to_period("W").dt.start_time
    by_coin = pos.groupby(["week", "coin"])["notional"].mean().unstack(fill_value=0) / 1e3
    top = by_coin.sum().nlargest(15).index
    days = pd.Index(milp.index[milp.index.hour == 0])
    weeks = pd.Index(days.tz_localize(None).to_period("W").start_time.unique())
    by_coin = by_coin.reindex(weeks, fill_value=0)
    deployed = (pos.groupby("ts")["notional"].sum().reindex(days, fill_value=0) * 1.5 / NAV * 100)
    deployed = deployed.groupby(deployed.index.tz_localize(None).to_period("W").start_time).mean()
    npos = pos.groupby("ts").size().reindex(days, fill_value=0)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=False, height_ratios=[1, 2.2])
    a1.fill_between(deployed.index, deployed, color=SERIES[0], alpha=0.25, lw=0)
    a1.plot(deployed.index, deployed, color=SERIES[0])
    a1.set_ylabel("% of NAV")
    a1.set_title(f"MILP allocator: capital tied up in positions (avg {npos.mean():.1f} positions; rest earns T-bills)")
    a1.set_ylim(0, 100)
    a1.margins(x=0)
    m = by_coin[top].T
    im = a2.imshow(m.to_numpy(), aspect="auto", cmap=BLUES, interpolation="nearest",
                   extent=[0, m.shape[1], m.shape[0], 0])
    a2.set_yticks(np.arange(len(top)) + 0.5, top)
    ticks = [i for i, w in enumerate(m.columns) if w.month in (1, 7) and w.day <= 7]
    a2.set_xticks(ticks, [m.columns[i].strftime("%b %Y") for i in ticks])
    a2.grid(False)
    a2.set_title("Weekly average position by coin, $k (15 most-used coins; Binance + Bybit)")
    fig.colorbar(im, ax=a2, fraction=0.025, pad=0.01, label="$k notional")
    fig.tight_layout()
    save(fig, "4_milp_positions.png")

    # 5. MILP trading by type.
    tr = milp.attrs["trades"]
    tr["kind"] = tr["kind"].replace({"open": "Opens and closes", "close": "Opens and closes",
                                     "resize": "Resizes", "liquidation": "Liquidations"})
    monthly = tr.groupby([tr["ts"].dt.tz_localize(None).dt.to_period("M").dt.start_time, "kind"])["notional"] \
        .sum().unstack(fill_value=0) / NAV * 100
    kinds = [k for k in ["Opens and closes", "Resizes", "Liquidations"] if k in monthly]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    bottom = np.zeros(len(monthly))
    for k, c in zip(kinds, SERIES, strict=False):
        ax.bar(monthly.index, monthly[k], bottom=bottom, width=24, color=c, label=k, edgecolor=SURFACE, linewidth=1)
        bottom += monthly[k].to_numpy()
    counts = tr.groupby("kind").size()
    yrs = (tr["ts"].max() - tr["ts"].min()).days / 365
    ax.set_title("MILP trading each month, % of NAV traded — "
                 + ", ".join(f"{k.lower()}: {counts.get(k, 0) / yrs:.0f}/yr" for k in kinds))
    ax.set_ylabel("% of NAV")
    ax.legend(loc="upper right")
    save(fig, "5_milp_trading.png")


if __name__ == "__main__":
    main()
