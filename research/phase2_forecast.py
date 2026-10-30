"""Phase 2: investable set, basis, and the pre-registered funding-forecast comparison.

Run after research/build_data.py:  python research/phase2_forecast.py
Writes reports/phase2/report.md. Spec and decision rule: docs/plan.md, "Phase 2 spec".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from funding.dataset import MAX_ABS_BASIS, VENUES, investable_rows, load
from funding.forecast import walk_forward

MODELS = ["M0_floor", "M1_last", "M2_ewma", "M3_regression"]
YEARS = range(2022, 2027)
PER_YEAR = 3 * 365
OUT = Path("reports/phase2/report.md")


def by_year(s):
    return s.groupby(s.index.get_level_values("ts").year)


def rank_ic(df: pd.DataFrame, model: str) -> pd.Series:
    """Spearman correlation between forecast and outcome across coins at each (venue, ts), then per year."""
    d = df[[model, "actual"]].dropna()
    keys = [d.index.get_level_values("venue"), d.index.get_level_values("ts")]
    ic = d.groupby(keys).apply(lambda g: g[model].rank().corr(g["actual"].rank()) if len(g) >= 5 else np.nan)
    ic.index.names = ["venue", "ts"]
    return by_year(ic.dropna()).mean()


def top_quintile_spread(df: pd.DataFrame, model: str) -> pd.Series:
    """Realised 7-day funding of the top fifth by forecast minus all investable coins, % a year."""
    d = df[[model, "actual"]].dropna()
    keys = [d.index.get_level_values("venue"), d.index.get_level_values("ts")]

    def spread(g):
        if len(g) < 5:
            return np.nan
        top = g[g[model] >= g[model].quantile(0.8)]
        return top["actual"].mean() - g["actual"].mean()

    s = d.groupby(keys).apply(spread)
    s.index.names = ["venue", "ts"]
    return by_year(s.dropna()).mean() * PER_YEAR * 100


def main():
    panels = load()
    out = ["# Phase 2: investable set, basis and funding forecasts\n\n"
           "Spec and decision rule fixed in advance: [docs/plan.md](../../docs/plan.md#phase-2-spec-funding-"
           "forecasts-fixed-2026-10-29-before-any-forecast-was-run). Out-of-sample period 2022-01 onwards.\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else ""))
        out.append(df.to_markdown(floatfmt=fmt) + "\n")

    # 1. Investable set
    rows = {}
    for v, p in panels.items():
        yr = p["member"].index.year
        n_member = p["member"].groupby(yr).sum().sum(axis=1)
        rows[f"{v} % with spot"] = (p["member"] & p["has_spot"]).groupby(yr).sum().sum(axis=1) / n_member * 100
        rows[f"{v} % investable"] = p["investable"].groupby(yr).sum().sum(axis=1) / n_member * 100
        rows[f"{v} avg investable coins"] = p["investable"].sum(axis=1).groupby(yr).mean()
    section("1. Investable set", pd.DataFrame(rows),
            "Share of universe coin-windows with a spot market on the same venue, and investable after "
            f"dropping |basis| > {MAX_ABS_BASIS:.0%} prints.", fmt=".1f")
    removed = pd.concat({v: (p["broken"] & p["member"] & p["has_spot"]).sum() for v, p in panels.items()}, axis=1)
    removed = removed[(removed > 0).any(axis=1)].sort_values(list(VENUES), ascending=False).head(10)
    out.append(f"\nCoins with the most windows removed by the {MAX_ABS_BASIS:.0%} basis rule (window counts):\n\n"
               + removed.to_markdown() + "\n")

    # 2. Basis
    stats = {}
    for v, p in panels.items():
        b = p["basis"].where(p["investable"]).stack()
        g = by_year(b.rename_axis(["ts", "coin"]))
        stats[f"{v} median (bp)"] = g.median() * 1e4
        stats[f"{v} 5th pct (bp)"] = g.quantile(0.05) * 1e4
        stats[f"{v} 95th pct (bp)"] = g.quantile(0.95) * 1e4
    section("2. Basis (perp / spot − 1) on investable coins", pd.DataFrame(stats),
            "Negative means the perp trades below spot; a short-perp/long-spot position entered then "
            "pays that discount back if the basis converges.")

    # 3. Forecasts
    rows = pd.concat({v: investable_rows(p) for v, p in panels.items()}, names=["venue"])
    fc = walk_forward(rows)
    err = pd.DataFrame({m: by_year((fc[m] - fc["actual"]).abs().dropna()).mean() * 1e4 for m in MODELS})
    err = err.loc[err.index.isin(YEARS)]
    section("3. Forecast error: 7-day mean funding (MAE, bp per 8h, out of sample)", err,
            "Lower is better. M2's half-life is re-chosen at each monthly refit on training data only.", fmt=".3f")
    half_lives = fc["m2_half_life"].groupby(fc.index.get_level_values("ts").year).agg(lambda s: s.value_counts()
                                                                                      .idxmax())
    out.append("\nM2 half-life chosen most often, by year: " + ", ".join(f"{y}: {h.split('_')[-1]}"
                                                                       for y, h in half_lives.items()) + "\n")
    section("4. Rank IC (Spearman, across investable coins at each time, mean by year)",
            pd.DataFrame({m: rank_ic(fc, m) for m in MODELS[1:]}), fmt=".3f")
    section("5. Economic value: realised 7-day funding, top fifth by forecast minus all coins (% a year)",
            pd.DataFrame({m: top_quintile_spread(fc, m) for m in MODELS[1:]}))

    # 6. Diagnostics (not part of the decision): where are the errors?
    first_seen = {(v, c): p["funding"][c].first_valid_index() for v, p in panels.items() for c in p["funding"]}
    d = fc.join(rows[["last"]])
    idx = d.index
    age_days = np.array([(t - first_seen[(v, c)]).days for v, t, c in idx])
    d["state"] = np.where((d["last"] - 1e-4).abs() < 1e-7, "at floor", np.where(d["last"] < 0, "negative",
                                                                                np.where(d["last"] < 1e-4, "0 to floor",
                                                                                         "above floor")))
    d["listing age"] = pd.cut(age_days, [-1, 90, 365, 10_000], labels=["< 90 days", "90-365 days", "> 1 year"])
    for col in ["state", "listing age"]:
        g = d.groupby(col, observed=True)
        diag = pd.DataFrame({m: g.apply(lambda x, m=m: (x[m] - x["actual"]).abs().mean() * 1e4) for m in MODELS})
        diag.insert(0, "share of rows %", g.size() / len(d) * 100)
        section(f"6{'ab'[col == 'listing age']}. Diagnostics: MAE by {col} (bp per 8h, all years)", diag, fmt=".2f")

    best_simple = err[["M1_last", "M2_ewma"]].min(axis=1)
    wins = (err["M3_regression"] < best_simple)
    # If M3 fails, "the simpler model" is whichever of M1/M2 has the lower average error.
    use = "M3_regression" if wins.sum() >= 4 else err[["M1_last", "M2_ewma"]].mean().idxmin()
    out.append(f"\n**Decision (rule fixed in advance):** M3 beats the better of M1/M2 in {int(wins.sum())} of "
               f"{len(wins)} years (need 4). **Model used downstream: {use}.**\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
