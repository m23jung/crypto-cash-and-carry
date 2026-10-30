"""Daily MILP allocator for spot/perp carry across two venues. Spec: docs/plan.md, "Phase 4 spec".

Solved with HiGHS through scipy.optimize.milp. Per candidate (venue, coin) the variables are
x (target notional), b (buy), s (sell) and y (position open, binary); per direction of transfer
between the two venues, g (amount) and z (transfer happens, binary).
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
    max_positions: int = 12
    venue_cap: float = 0.60  # of NAV, after transfers
    min_transfer: float = 50_000.0
    transfer_fee: float = 10.0
    transfers: bool = True  # False = fixed split (ablation A1)
    per_coin_caps: bool = True  # False = liquidity cap only (ablation A2)
    exit_cost: bool = False  # Phase 4b: sells also pay the exit half of the round trip
    band_abs: float = 0.0  # Phase 4b no-trade band: a held position trades by at least
    band_rel: float = 0.0  # max(band_abs, band_rel x position), or not at all (full close always allowed)


def solve(cands: pd.DataFrame, equity: dict[str, float], incoming: dict[str, float], nav: float,
          tbill: float, p: Params) -> tuple[pd.Series, dict[tuple[str, str], float]]:
    """One day's allocation.

    ``cands`` has one row per (venue, coin) with columns: forecast (annual), x0 (current notional),
    margin (capital per $1 notional), cost (round trip, fraction), adv_cap ($), age_days.
    ``equity`` is each venue's equity now; ``incoming`` is capital already in transit to each venue.
    Returns target notional per (venue, coin) and the transfers to make {(from, to): amount}.
    """
    venues = sorted(equity)
    n = len(cands)
    major = cands.index.get_level_values("coin").isin(MAJORS)
    young = (cands["age_days"] < p.young_days).to_numpy() & ~major
    kind = np.where(major, "major", np.where(young, "young", "other"))
    h = p.horizon_days / 365
    margin, x0 = cands["margin"].to_numpy(), cands["x0"].to_numpy()
    carry = (cands["forecast"].to_numpy() - margin * tbill - np.vectorize(p.penalty.get)(kind)) * h

    venue_of = cands.index.get_level_values("venue").to_numpy()
    eq_v = np.array([equity[v] for v in venue_of])
    share = {"major": p.cap_major, "other": p.cap_other, "young": p.cap_young}
    cap = np.vectorize(share.get)(kind) * eq_v if p.per_coin_caps else np.full(n, np.inf)
    upper = np.maximum(np.minimum(cap, cands["adv_cap"].to_numpy()), x0)  # never force-sell for drift
    lower = np.where(x0 > 0, np.minimum(p.min_position, x0), p.min_position)

    # Variable layout: [x, b, s, y, t (n each), g(2), z(2)]; t = "this position trades today" (binary);
    # g[0]: venues[0] -> venues[1], g[1]: reverse.
    nv = 5 * n + 4
    X, B, S, Y, T = (np.arange(n) + k * n for k in range(5))
    G, Z = 5 * n + np.arange(2), 5 * n + 2 + np.arange(2)
    c = np.zeros(nv)
    c[X], c[B] = -carry, cands["cost"].to_numpy()
    if p.exit_cost:
        c[S] = cands["cost"].to_numpy() / 2
    c[G], c[Z] = tbill / 365, p.transfer_fee
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
    add({int(i): 1 for i in Y}, 0, p.max_positions)
    for k, v in enumerate(venues):
        out, inn = G[k], G[1 - k]
        js = np.flatnonzero(venue_of == v)
        # Capital: positions planned with today's equity, minus what leaves, plus what is arriving.
        add({**{int(X[j]): margin[j] for j in js}, out: 1, inn: -1}, -np.inf, equity[v] + incoming.get(v, 0.0))
        if p.transfers:
            add({out: -1, inn: 1}, -np.inf, p.venue_cap * nav - equity[v] - incoming.get(v, 0.0))
    for k in range(2):
        add({G[k]: 1, Z[k]: -p.min_transfer}, 0, np.inf)
        add({G[k]: 1, Z[k]: -nav}, -np.inf, 0)

    ub = np.full(nv, np.inf)
    ub[S], ub[Y], ub[T], ub[Z] = x0, 1, 1, 1
    if not p.transfers:
        ub[G], ub[Z] = 0, 0
    integrality = np.zeros(nv)
    integrality[Y], integrality[T], integrality[Z] = 1, 1, 1
    res = milp(c, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality,
               bounds=Bounds(np.zeros(nv), ub), options={"time_limit": 10})
    if res.x is None:
        raise RuntimeError(f"MILP failed: {res.message}")
    x = pd.Series(np.where(res.x[Y] > 0.5, res.x[X], 0.0), index=cands.index)
    g = res.x[G]
    transfers = {(venues[0], venues[1]): g[0], (venues[1], venues[0]): g[1]}
    return x, {k: v for k, v in transfers.items() if v > 1.0}


def make_allocator(forecast: pd.Series, panels: dict, tbill: pd.Series, params: Params, per_year: int = 3 * 365):
    """Daily decision function for backtest.run_joint. ``forecast`` is mean funding per 8h, indexed
    (venue, ts, coin); ``tbill`` is per 8h. Held coins without a forecast that day are kept unchanged."""
    by_vt = {key: g.droplevel(["venue", "ts"]) for key, g in forecast.groupby(level=["venue", "ts"])}
    first_seen = {(v, c): p["funding"][c].first_valid_index() for v, p in panels.items() for c in p["funding"]}

    def decide(t, books, transit):
        rows, keep = [], {}
        for v, b in books.items():
            fc = by_vt.get((v, t), pd.Series(dtype=float))
            for c in b.inv:
                f = fc.get(c, np.nan)
                held = b.notional(c) if c in b.q else 0.0
                if not np.isfinite(f):
                    if held:
                        keep.setdefault(v, {})[c] = np.nan  # hold as is
                    continue
                rows.append({"venue": v, "coin": c, "forecast": f * per_year, "x0": held, "margin": b.margin(c),
                             "cost": b.costs.round_trip, "adv_cap": b.adv_cap(c),
                             "age_days": (t - first_seen[(v, c)]).days})
        equity = {v: b.equity for v, b in books.items()}
        incoming = {}
        for _, dst, amount in transit:
            incoming[dst] = incoming.get(dst, 0.0) + amount
        nav = sum(equity.values()) + sum(incoming.values())
        targets = {v: dict(d) for v, d in keep.items()}
        if not rows:
            return targets, {}
        cands = pd.DataFrame(rows).set_index(["venue", "coin"])
        x, transfers = solve(cands, equity, incoming, nav, tbill.get(t, 0.0) * per_year, params)
        for (v, c), amount in x.items():
            unchanged = abs(amount - cands.at[(v, c), "x0"]) < 1.0 and amount > 0
            targets.setdefault(v, {})[c] = np.nan if unchanged else amount  # NaN = hold, don't chase drift
        return targets, transfers

    return decide
