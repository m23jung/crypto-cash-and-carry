"""Daily MILP allocator for spot/perp carry on one venue. Spec: docs/plan.md, "Phase 4 spec".

Solved with HiGHS through scipy.optimize.milp. Per candidate coin the variables are x (target
notional), b (buy), s (sell), y (position open, binary), t (position trades today, binary) and
d (the trade is a buy, binary; stops a buy-and-sell wash from meeting the no-trade band).
Each venue is its own book; the multi-venue version with capital transfers is in git history (f232ab5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

MAJORS = ("BTC", "ETH")


@dataclass(frozen=True)
class Params:
    horizon_days: float = 30.0
    cap_major: float = 0.25  # of venue equity, for new buying
    cap_other: float = 0.10
    cap_young: float = 0.05  # listed under young_days
    young_days: int = 90
    penalty: dict = field(default_factory=lambda: {"major": 0.0, "other": 0.03, "young": 0.10})  # a year
    min_position: float = 10_000.0
    max_positions: int = 6  # per venue
    per_coin_caps: bool = True  # False = liquidity cap only (ablation A2)
    exit_cost: bool = False  # Phase 4b: sells also pay the exit half of the round trip
    band_abs: float = 0.0  # Phase 4b no-trade band: a held position trades by at least
    band_rel: float = 0.0  # max(band_abs, band_rel x position), or not at all (full close always allowed)


def solve(cands: pd.DataFrame, equity: float, tbill: float, p: Params) -> pd.Series:
    """One day's allocation for one venue.

    ``cands`` has one row per coin with columns: forecast (annual), x0 (current notional),
    margin (capital per $1 notional), cost (round trip, fraction), adv_cap ($), age_days.
    Returns target notional per coin.
    """
    n = len(cands)
    major = cands.index.isin(MAJORS)
    young = (cands["age_days"] < p.young_days).to_numpy() & ~major
    kind = np.where(major, "major", np.where(young, "young", "other"))
    h = p.horizon_days / 365
    margin, x0 = cands["margin"].to_numpy(), cands["x0"].to_numpy()
    carry = (cands["forecast"].to_numpy() - margin * tbill - np.vectorize(p.penalty.get)(kind)) * h

    share = {"major": p.cap_major, "other": p.cap_other, "young": p.cap_young}
    cap = np.vectorize(share.get)(kind) * equity if p.per_coin_caps else np.full(n, np.inf)
    upper = np.maximum(np.minimum(cap, cands["adv_cap"].to_numpy()), x0)  # never force-sell for drift
    lower = np.where(x0 > 0, np.minimum(p.min_position, x0), p.min_position)

    # Variable layout: [x, b, s, y, t, d], n each.
    nv = 6 * n
    X, B, S, Y, T, D = (np.arange(n) + k * n for k in range(6))
    c = np.zeros(nv)
    c[X], c[B] = -carry, cands["cost"].to_numpy()
    if p.exit_cost:
        c[S] = cands["cost"].to_numpy() / 2
    rows, lo, hi = [], [], []

    def add(coefs: dict, lb: float, ub: float):
        r = np.zeros(nv)
        for i, v in coefs.items():
            r[i] += v
        rows.append(r), lo.append(lb), hi.append(ub)

    for j in range(n):
        add({X[j]: 1, B[j]: -1, S[j]: 1}, x0[j], x0[j])  # x = x0 + b - s
        add({X[j]: 1, Y[j]: -upper[j]}, -np.inf, 0)  # x <= upper * y
        add({X[j]: 1, Y[j]: -lower[j]}, 0, np.inf)  # x >= lower * y
        band = min(max(p.band_abs, p.band_rel * x0[j]), x0[j]) if x0[j] > 0 else 0.0
        big = max(upper[j], x0[j], 1.0)
        add({B[j]: 1, S[j]: 1, T[j]: -big}, -np.inf, 0)  # trade only if t = 1
        add({B[j]: 1, S[j]: 1, T[j]: -band}, 0, np.inf)  # ...and then by at least the band
        add({B[j]: 1, D[j]: -big}, -np.inf, 0)  # buy only if d = 1
        add({S[j]: 1, D[j]: big}, -np.inf, big)  # sell only if d = 0
    add({int(i): 1 for i in Y}, 0, p.max_positions)
    add({int(X[j]): margin[j] for j in range(n)}, -np.inf, equity)  # capital

    ub = np.full(nv, np.inf)
    ub[S], ub[Y], ub[T], ub[D] = x0, 1, 1, 1
    integrality = np.zeros(nv)
    integrality[Y], integrality[T], integrality[D] = 1, 1, 1
    res = milp(c, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality,
               bounds=Bounds(np.zeros(nv), ub), options={"time_limit": 10})
    if res.x is None:
        raise RuntimeError(f"MILP failed: {res.message}")
    return pd.Series(np.where(res.x[Y] > 0.5, res.x[X], 0.0), index=cands.index)


def make_allocator(forecast: pd.Series, panel: dict, tbill: pd.Series, params: Params, per_year: int = 3 * 365):
    """Daily decision function for backtest.run_daily. ``forecast`` is mean funding per 8h for this venue,
    indexed (ts, coin); ``tbill`` is per 8h. Held coins without a forecast that day are kept unchanged."""
    by_t = {t: g.droplevel("ts") for t, g in forecast.groupby(level="ts")}
    first_seen = {c: panel["funding"][c].first_valid_index() for c in panel["funding"]}

    def decide(t, b):
        fc, rows, targets = by_t.get(t, pd.Series(dtype=float)), [], {}
        for c in b.inv:
            f = fc.get(c, np.nan)
            held = b.notional(c) if c in b.q else 0.0
            if not np.isfinite(f):
                if held:
                    targets[c] = np.nan  # hold as is
                continue
            rows.append({"coin": c, "forecast": f * per_year, "x0": held, "margin": b.margin(c),
                         "cost": b.costs.round_trip, "adv_cap": b.adv_cap(c), "age_days": (t - first_seen[c]).days})
        if not rows:
            return targets
        cands = pd.DataFrame(rows).set_index("coin")
        for c, amount in solve(cands, b.equity, tbill.get(t, 0.0) * per_year, params).items():
            unchanged = abs(amount - cands.at[c, "x0"]) < 1.0 and amount > 0
            targets[c] = np.nan if unchanged else amount  # NaN = hold, don't chase drift
        return targets

    return decide
