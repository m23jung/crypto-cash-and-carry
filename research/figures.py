"""Paper figures: returns, forecasts, P&L sources, cost of capital, MILP positions and trading, margin.

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
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from phase3_backtest import BASELINE, COSTS, NAV, START, STRATEGIES, attribution, backtest, daily_excess  # noqa: E402
from phase4_allocator import milp_backtest  # noqa: E402

from funding.backtest import Costs, run  # noqa: E402
from funding.dataset import VENUES, investable_rows, load, tbill_8h  # noqa: E402
from funding.forecast import walk_forward  # noqa: E402
from funding.milp import Params  # noqa: E402

OUT = Path("reports/figures")
# One blue family plus gray, so every chart matches; series also differ by line style and direct labels.
NAVY, BLUE, LIGHT, GRAY = "#0d366b", "#3987e5", "#86b6ef", "#7a7974"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#111111", "#52514e", "#898781", "#e6e5df", "#c3c2b7", "#ffffff"
POS, NEG = BLUE, "#d0574f"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f4f3f0", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", NAVY])
FONT = "/System/Library/Fonts/Supplemental/Charter.ttc"  # same face as the PDF body (research/export_pdf.py)
PER_YEAR = 3 * 365

if Path(FONT).exists():
    font_manager.fontManager.addfont(FONT)
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": ["Charter", "serif"], "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "lines.linewidth": 1.8, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "legend.frameon": False, "axes.unicode_minus": True,
})


def pct(v: float, digits: int = 1) -> str:
    """Signed percentage with a true minus sign, to match the axis labels."""
    return f"{v:+.{digits}f}%".replace("-", "\u2212")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("wrote", OUT / name)


def label_line_ends(ax, series: dict[str, pd.Series], colors: dict[str, str]):
    """Direct labels just right of each line's last point, nudged apart so they don't collide."""
    ends = sorted(((s.dropna().iloc[-1], name) for name, s in series.items()), reverse=True)
    lo, hi = ax.get_ylim()
    gap, placed = (hi - lo) * 0.07, []
    for y, name in ends:
        y_text = min(y, placed[-1] - gap) if placed else y
        placed.append(y_text)
        x = series[name].dropna().index[-1]
        ax.plot([x], [y], "o", ms=5, color=colors[name], mec=SURFACE, mew=1.5, zorder=5, clip_on=False)
        ax.annotate(f"{name}  {pct(y)}", (x, y), xytext=(1.01, y_text), textcoords=("axes fraction", "data"),
                    va="center", fontsize=9, color=INK, annotation_clip=False)


def forecast_figure(fc7: pd.DataFrame, costs: Costs) -> None:
    """Accuracy by model, realised funding by forecast quintile, and the top quintile's edge vs rotation cost."""
    fc = fc7[fc7.index.get_level_values("ts") >= pd.Timestamp(START, tz="UTC")].dropna(subset=["actual"])
    names = {"M0_floor": "Floor", "M1_last": "Last\nvalue", "M2_ewma": "EWMA", "M3_regression": "Regression"}
    mae = pd.Series({lab: (fc[m] - fc["actual"]).abs().mean() * 1e4 for m, lab in names.items()})

    d = fc.dropna(subset=["M3_regression"]).reset_index()
    d["q"] = d.groupby(["venue", "ts"])["M3_regression"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1 if len(s) >= 5 else np.nan)
    d = d.dropna(subset=["q"])
    by_q = d.groupby("q")[["actual", "M3_regression"]].mean() * PER_YEAR * 100
    edge = (by_q.loc[5, "actual"] - d["actual"].mean() * PER_YEAR * 100)

    # Weekly rotation into the top quintile: share of the basket replaced each week x one round trip.
    first = d["ts"].min()
    weekly = d[((d["ts"] - first) / pd.Timedelta(hours=8)) % 21 == 0]
    replaced = []
    for _, g in weekly[weekly["q"] == 5].groupby("venue"):
        sets = g.groupby("ts")["coin"].apply(set)
        replaced += [len(b - a) / len(b) for a, b in zip(sets.iloc[:-1], sets.iloc[1:], strict=True) if b]
    rotation = np.mean(replaced) * costs.round_trip * 52 * 100

    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(11.5, 4.2), width_ratios=[1, 1.2, 1])
    a1.bar(mae.index, mae, color=[LIGHT, LIGHT, LIGHT, NAVY], width=0.65)
    for i, v in enumerate(mae):
        a1.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    a1.set_title("Forecast error")
    a1.set_ylabel("mean absolute error, bp per 8 hours")
    a1.set_ylim(0, mae.max() * 1.18)
    a1.grid(axis="x", visible=False)

    x = by_q.index.astype(int)
    a2.bar(x, by_q["actual"], color=BLUES(np.linspace(0.3, 1, 5)), width=0.65, label="realised")
    a2.plot(x, by_q["M3_regression"], "o", color=INK, ms=6, mec=SURFACE, mew=1.5, label="forecast")
    for xi, v in zip(x, by_q["actual"], strict=True):
        a2.text(xi, max(v, 0), pct(v).lstrip("+"), ha="center", va="bottom", fontsize=9, color=INK)
    a2.axhline(0, color=AXIS, lw=1)
    a2.set_xticks(x, ["1\nlowest", "2", "3", "4", "5\nhighest"])
    a2.set_title("Realised funding by forecast quintile")
    a2.set_ylabel("next-7-day funding, % a year")
    a2.set_ylim(min(0, by_q.min().min()) * 1.25, by_q.max().max() * 1.18)
    a2.legend(loc="upper left")
    a2.grid(axis="x", visible=False)

    parts = [("Extra funding,\ntop quintile", edge, POS), ("Weekly\nrotation cost", -rotation, NEG)]
    start = 0.0
    for i, (_, v, c) in enumerate(parts):
        a3.bar(i, v, bottom=start, color=c, width=0.6)
        a3.text(i, start + max(v, 0), pct(v), ha="center", va="bottom", fontsize=9)
        start += v
    a3.bar(2, start, color=GRAY, width=0.6)
    a3.text(2, max(start, 0), pct(start), ha="center", va="bottom", fontsize=9, fontweight="bold")
    a3.axhline(0, color=AXIS, lw=1)
    a3.set_xticks(range(3), [p[0] for p in parts] + ["Net"])
    a3.set_title("Edge vs cost")
    a3.set_ylabel("% a year, vs the average coin")
    a3.set_ylim(min(0, start) - 2, edge * 1.18)
    a3.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=2)
    save(fig, "8_forecasts.png")
    print(f"forecast figure: MAE {mae.round(2).to_dict()}, top-quintile edge {edge:.1f}%, "
          f"replaced per week {np.mean(replaced):.0%}, rotation cost {rotation:.1f}%")


def main():
    panels = load()
    tbill = tbill_8h(panels["binance"]["funding"].index).fillna(0.0)
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc7, fc30 = walk_forward(rows), walk_forward(rows, target="target_30d")
    forecast_figure(fc7, COSTS["binance"])

    ledgers = {"Passive BTC+ETH": backtest(panels, fc7, tbill, BASELINE)}
    factory, model, slots = STRATEGIES["S3 cost-aware top-5"]
    s3_logs = {v: {} for v in VENUES}
    s3 = [run(panels[v], fc7[model].xs(v, level="venue"), factory(COSTS[v]), slots, NAV / 2, tbill, COSTS[v], START,
              log=s3_logs[v]) for v in VENUES]
    cols = ["equity_start", "pnl", "n_held", "liquidations", "funding", "basis", "unhedged", "costs",
            "liquidation", "cash", "traded"]
    ledgers["Cost-aware top 5"] = sum(b[cols] for b in s3).assign(tbill=s3[0]["tbill"])
    trades = {"Cost-aware top 5": pd.concat([s3_logs[v]["trades"].assign(venue=v) for v in VENUES])}
    cross = {v: dataclasses.replace(c, margin_buffer=0.10) for v, c in COSTS.items()}
    books = [run(panels[v], pd.Series(dtype=float), STRATEGIES[BASELINE][0](cross[v]), 2, NAV / 2, tbill, cross[v],
                 START) for v in VENUES]
    ledgers["Passive, cross-margin"] = sum(b[cols] for b in books).assign(tbill=books[0]["tbill"])
    print("running MILP")
    milp = milp_backtest(panels, fc30["M3_regression"], tbill, Params())
    trades["MILP"], positions = milp.attrs["trades"], milp.attrs["positions"]
    milp.attrs = {}  # keep logs out of pandas metadata before combining frames
    ledgers["MILP"] = milp
    order = ["Passive, cross-margin", "Passive BTC+ETH", "Cost-aware top 5", "MILP"]
    colors = dict(zip(order, [NAVY, BLUE, LIGHT, GRAY], strict=True))
    styles = dict(zip(order, ["-", "-", "-", (0, (5, 2))], strict=True))

    # 1. Cumulative excess return.
    fig, ax = plt.subplots(figsize=(10, 5))
    cum = {n: daily_excess(ledgers[n]).cumsum() * 100 for n in order}
    for n in order:
        ax.plot(cum[n].index, cum[n], color=colors[n], ls=styles[n], label=n)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_title("Cumulative excess return over T-bills")
    ax.set_ylabel("% of capital")
    ax.margins(x=0.01)
    lo, hi = min(c.min() for c in cum.values()), max(c.max() for c in cum.values())
    ax.set_ylim(lo - 0.12 * (hi - lo), hi + 0.08 * (hi - lo))
    label_line_ends(ax, cum, colors)
    events = []  # the largest one-day losses: short-perp liquidations in price spikes
    for n, tr in trades.items():
        daily = daily_excess(ledgers[n]) * 100
        liq = tr[tr["kind"] == "liquidation"].assign(day=lambda d: d["ts"].dt.floor("D"))
        for d, loss in daily[daily <= -0.5].nsmallest(3).items():
            hit = liq[(liq["day"] >= d - pd.Timedelta(days=1)) & (liq["day"] <= d)]["coin"].unique()
            events.append((d, n, loss, f"{'/'.join(hit)} liquidated" if len(hit) else "one-day basis move"))
    key = []
    for i, (d, n, loss, text) in enumerate(sorted(events), 1):
        y = cum[n].loc[d]
        ax.plot([d], [y], "o", ms=13, mfc=SURFACE, mec=colors[n], mew=1.5, zorder=6)
        ax.text(d, y, str(i), ha="center", va="center", fontsize=7.5, fontweight="bold", color=INK, zorder=7)
        key.append(f"{i}  {d:%b %Y}  {text} ({n}, {pct(loss)})")
    ax.text(0.99, 0.03, "\n".join(key), transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            color=INK2, multialignment="left", bbox={"boxstyle": "round,pad=0.4", "fc": SURFACE, "ec": GRID})
    ax.legend(loc="upper left", ncols=2)
    save(fig, "1_cumulative_excess_return.png")

    # 2. Where the P&L comes from (waterfall per strategy, % of capital a year).
    parts = {"funding": "Fund-\ning", "basis": "Basis", "unhedged": "Un-\nhedged", "costs": "Costs",
             "liquidation": "Liqui-\ndation", "cash minus T-bill on NAV": "Cash −\nT-bill"}
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 4.4), sharey=True)
    attr = {n: attribution(ledgers[n]) for n in order}
    top = max(max(np.cumsum([a[k] for k in parts]).max(), a["total excess"]) for a in attr.values())
    bottom = min(min(np.cumsum([a[k] for k in parts]).min(), a["total excess"], 0) for a in attr.values())
    for ax, n in zip(axes, order, strict=True):
        a = attr[n]
        vals, start = [a[k] for k in parts], 0.0
        for i, v in enumerate(vals):
            ax.bar(i, v, bottom=start, color=POS if v >= 0 else NEG, width=0.72)
            start += v
        ax.bar(len(vals), a["total excess"], color=GRAY, width=0.72)
        ax.axhline(0, color=AXIS, lw=1)
        ax.set_xticks(range(len(vals) + 1), [*parts.values(), "Total"], fontsize=7.5)
        ax.set_title(f"{n}: {pct(a['total excess'], 2)}", fontsize=10.5)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylim(bottom - 0.5, top + 0.8)
    axes[0].set_ylabel("% of capital a year")
    fig.suptitle("Excess return by source", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    save(fig, "2_pnl_attribution.png")

    # 3. Funding vs the cost of capital, from the start of the data.
    f = panels["binance"]["funding"]["BTC"]
    daily = f.groupby(f.index.floor("D")).sum() * 365 * 100
    t_ann = tbill.groupby(tbill.index.floor("D")).sum().reindex(daily.index) * 365 * 100
    daily, t_ann = daily.iloc[:-1], t_ann.iloc[:-1]  # drop today's partial day
    lines = [("BTC funding, 30-day average", daily.rolling(30).mean(), BLUE, "-"),
             ("Capital cost at margin 1.5", t_ann * 1.5, NAVY, "-"),
             ("Capital cost at margin 1.1", t_ann * 1.1, NAVY, (0, (4, 2)))]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axvspan(daily.index[0], pd.Timestamp(START, tz="UTC"), color=GRID, alpha=0.6, lw=0)
    ax.text(daily.index[10], 0.22, "forecast training\n(before backtests)", transform=ax.get_xaxis_transform(),
            va="bottom", fontsize=8.5, color=INK2)
    for n, s, c, ls in lines:
        ax.plot(s.index, s, color=c, ls=ls, label=n)
    ax.axhline(10.95, color=MUTED, lw=1, ls=(0, (1, 2)))
    ax.text(1.0, 10.95, " floor 10.95%", transform=ax.get_yaxis_transform(), va="center", fontsize=9, color=INK2)
    ax.axhline(0, color=AXIS, lw=1)
    cap = 50  # 2021 peaks would flatten 2022-26; label the off-scale peak instead
    peak = lines[0][1]
    ax.set_ylim(min(-8, peak.min() - 2), cap)
    ax.annotate(f"peak {peak.max():.0f}% ({peak.idxmax():%b %Y}), off scale", (peak.idxmax(), cap),
                xytext=(60, -14), textcoords="offset points", fontsize=8.5, color=INK2,
                arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8})
    ax.set_title("BTC funding vs cost of capital")
    ax.set_ylabel("% a year")
    ax.margins(x=0.01)
    ax.legend(loc="upper right")
    save(fig, "3_funding_vs_capital_cost.png")

    # 4. MILP positions over time.
    pos = positions
    pos["week"] = pos["ts"].dt.tz_localize(None).dt.to_period("W").dt.start_time
    by_coin = pos.groupby(["week", "coin"])["notional"].mean().unstack(fill_value=0) / 1e3
    top15 = by_coin.sum().nlargest(15).index
    days = pd.Index(milp.index[milp.index.hour == 0])
    weeks = pd.Index(days.tz_localize(None).to_period("W").start_time.unique())
    by_coin = by_coin.reindex(weeks, fill_value=0)
    deployed = (pos.groupby("ts")["notional"].sum().reindex(days, fill_value=0) * 1.5 / NAV * 100)
    deployed = deployed.groupby(deployed.index.tz_localize(None).to_period("W").start_time).mean()
    npos = pos.groupby("ts").size().reindex(days, fill_value=0)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7.5), height_ratios=[1, 2.2])
    a1.fill_between(deployed.index, deployed, color=BLUE, alpha=0.25, lw=0)
    a1.plot(deployed.index, deployed, color=BLUE)
    a1.set_ylabel("% of capital")
    a1.set_title(f"MILP: capital in positions (average {npos.mean():.1f} positions)")
    a1.set_ylim(0, max(100, deployed.max()) * 1.08)
    a1.margins(x=0)
    m = by_coin[top15].T
    im = a2.imshow(m.to_numpy(), aspect="auto", cmap=BLUES, interpolation="nearest",
                   extent=[0, m.shape[1], m.shape[0], 0])
    a2.set_yticks(np.arange(len(top15)) + 0.5, top15)
    ticks = [i for i, w in enumerate(m.columns) if w.month in (1, 7) and w.day <= 7]
    a2.set_xticks(ticks, [m.columns[i].strftime("%b %Y") for i in ticks])
    a2.grid(False)
    a2.set_title("MILP: weekly position by coin, $k (15 most used)")
    fig.colorbar(im, ax=a2, fraction=0.025, pad=0.01, label="$k notional")
    fig.tight_layout()
    save(fig, "4_milp_positions.png")

    # 5. MILP trading by type.
    tr = trades["MILP"].copy()
    tr["kind"] = tr["kind"].replace({"open": "Opens and closes", "close": "Opens and closes",
                                     "resize": "Resizes", "liquidation": "Liquidations"})
    monthly = tr.groupby([tr["ts"].dt.tz_localize(None).dt.to_period("M").dt.start_time, "kind"])["notional"] \
        .sum().unstack(fill_value=0) / NAV * 100
    kinds = [k for k in ["Opens and closes", "Resizes", "Liquidations"] if k in monthly]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    base = np.zeros(len(monthly))
    for k, c in zip(kinds, [NAVY, LIGHT, NEG], strict=False):
        ax.bar(monthly.index, monthly[k], bottom=base, width=24, color=c, label=k, edgecolor=SURFACE, linewidth=1)
        base += monthly[k].to_numpy()
    counts = tr.groupby("kind").size()
    yrs = (tr["ts"].max() - tr["ts"].min()).days / 365
    ax.set_title("MILP: monthly trading")
    ax.set_ylabel("% of capital traded")
    ax.set_ylim(0, base.max() * 1.1)
    ax.legend(loc="upper right", labels=[f"{k} ({counts.get(k, 0) / yrs:.0f} a year)" for k in kinds])
    save(fig, "5_milp_trading.png")


def margin_figure() -> None:
    """Figure 7: passive BTC+ETH excess return vs margin factor (read from reports/sensitivity/report.md)."""
    text = Path("reports/sensitivity/report.md").read_text().split("## B.")[0]
    rows = [r.split("|") for r in text.splitlines()
            if r.strip().startswith("|") and r.split("|")[1].strip()[:1].isdigit()]
    m = pd.DataFrame({"margin": [float(r[1]) for r in rows], "excess": [float(r[2]) for r in rows],
                      "sharpe": [float(r[3]) for r in rows]})
    fig, ax = plt.subplots(figsize=(9, 4.6))
    span = m["excess"].max() - m["excess"].min()
    ax.set_ylim(m["excess"].min() - 0.15 * span, m["excess"].max() + 0.15 * span)
    ax.set_xlim(m["margin"].min() - 0.05, m["margin"].max() + 0.08)
    ax.axvspan(1.0, 1.05, color=LIGHT, alpha=0.25, lw=0)
    ax.text(1.005, 0.04, "portfolio\nmargin", transform=ax.get_xaxis_transform(), fontsize=8.5, color=INK2)
    ax.axvline(1.5, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(1.51, 0.04, "separate\naccounts", transform=ax.get_xaxis_transform(), fontsize=8.5, color=INK2)
    ax.axhline(0, color=AXIS, lw=1)
    ax.plot(m["margin"], m["excess"], color=BLUE, marker="o", ms=6, mec=SURFACE, mew=1.5)
    for _, r in m.iterrows():
        ax.annotate(pct(r["excess"], 2), (r["margin"], r["excess"]), xytext=(6, 6), textcoords="offset points",
                    fontsize=8.5, color=INK)
    be = np.interp(0, m["excess"][::-1], m["margin"][::-1])
    ax.plot([be], [0], "o", ms=7, color=NEG, mec=SURFACE, mew=1.5, zorder=5)
    ax.annotate(f"break-even ≈ {be:.2f}", (be, 0), xytext=(-100, -18), textcoords="offset points", fontsize=9,
                color=INK)
    ax.set_xlabel("margin factor: capital per $1 of notional")
    ax.set_ylabel("excess return, % a year")
    ax.set_title("Passive BTC+ETH: return vs margin factor")
    save(fig, "7_margin_sensitivity.png")


if __name__ == "__main__":
    margin_figure()
    main()
