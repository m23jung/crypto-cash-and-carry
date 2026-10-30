"""Funding forecasts: features, the four pre-registered models and a leak-free walk-forward.

Spec: docs/plan.md, "Phase 2 spec". All quantities are per 8-hour window, as fractions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 0.0001
WINDOWS_PER_DAY = 3
HORIZON = 21  # 7 days
TARGET_WINDOWS = {"target_1d": 1 * WINDOWS_PER_DAY, "target_7d": HORIZON, "target_30d": 30 * WINDOWS_PER_DAY}
EWMA_DAYS = (1, 7, 30)  # M3 features
M2_HALF_LIVES = (1, 3, 7, 30)  # days; M2 picks one on training data
FEATURES = ["last", "ewm_1d", "ewm_7d", "ewm_30d", "basis", "floor_share_3d"]


def forward_mean(funding: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Mean funding over windows t+1..t+horizon; NaN unless all of them are observed."""
    fwd = funding[::-1].rolling(horizon, min_periods=horizon).mean()[::-1]
    return fwd.shift(-1)


def ewma(funding: pd.DataFrame, half_life_days: float) -> pd.DataFrame:
    return funding.ewm(halflife=half_life_days * WINDOWS_PER_DAY, min_periods=WINDOWS_PER_DAY).mean()


def features(funding: pd.DataFrame, basis: pd.DataFrame) -> pd.DataFrame:
    """Long table indexed (ts, coin): features known at t, plus targets. One venue at a time."""
    cols = {
        "last": funding,
        **{f"ewm_{d}d": ewma(funding, d) for d in EWMA_DAYS},
        **{f"m2_hl_{d}d": ewma(funding, d) for d in M2_HALF_LIVES},
        "basis": basis.reindex_like(funding),
        "floor_share_3d": ((funding - FLOOR).abs() < 1e-7).astype(float).where(funding.notna())
        .rolling(3 * WINDOWS_PER_DAY, min_periods=3 * WINDOWS_PER_DAY).mean(),
        **{name: forward_mean(funding, n) for name, n in TARGET_WINDOWS.items()},
    }
    return pd.concat({k: v.stack() for k, v in cols.items()}, axis=1).rename_axis(["ts", "coin"])


def walk_forward(rows: pd.DataFrame, first_test: str = "2022-01-01", target: str = "target_7d") -> pd.DataFrame:
    """Out-of-sample forecasts for M0-M3, refit at each month start on an expanding window.

    ``rows`` is the investable long table (any number of venues stacked). A training row at time t is
    used at refit date R only if its target ends before R: t + (target length) windows <= R.
    """
    ts = rows.index.get_level_values("ts")
    gap = pd.Timedelta(hours=8 * TARGET_WINDOWS[target])
    out = []
    for start in pd.date_range(first_test, ts.max().tz_localize(None), freq="MS").tz_localize("UTC"):
        end = start + pd.offsets.MonthBegin(1)
        test = rows[(ts >= start) & (ts < end)]
        train = rows[ts <= start - gap].dropna(subset=[target])
        if test.empty or train.empty:
            continue
        m2_cols = [f"m2_hl_{d}d" for d in M2_HALF_LIVES]
        m2_mae = {c: (train[c] - train[target]).abs().mean() for c in m2_cols}
        m2_best = min(m2_mae, key=m2_mae.get)
        fit = train.dropna(subset=FEATURES)
        x = np.column_stack([np.ones(len(fit)), fit[FEATURES].to_numpy()])
        beta, *_ = np.linalg.lstsq(x, fit[target].to_numpy(), rcond=None)
        complete = test[FEATURES].notna().all(axis=1)
        m3 = pd.Series(np.nan, index=test.index)
        m3[complete] = np.column_stack([np.ones(complete.sum()), test.loc[complete, FEATURES].to_numpy()]) @ beta
        out.append(pd.DataFrame({
            "M0_floor": FLOOR, "M1_last": test["last"], "M2_ewma": test[m2_best], "M3_regression": m3,
            "m2_half_life": m2_best, "actual": test[target],
        }, index=test.index))
    return pd.concat(out)
