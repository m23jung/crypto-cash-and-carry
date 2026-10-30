"""Performance statistics on daily excess returns, including multiple-testing-aware Sharpe inference."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DAYS = 365  # crypto trades every day
EULER_GAMMA = 0.5772156649


def sharpe(r: pd.Series) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(DAYS)) if sd > 0 else np.nan


def max_drawdown(r: pd.Series) -> float:
    wealth = (1 + r).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def probabilistic_sharpe(r: pd.Series, benchmark: float = 0.0) -> float:
    """P(true Sharpe > benchmark), adjusting for sample length, skew and fat tails (Bailey & Lopez de Prado 2012).
    ``benchmark`` is annualised."""
    n, sd = len(r), r.std(ddof=1)
    if n < 3 or sd == 0:
        return np.nan
    sr, sr0 = r.mean() / sd, benchmark / np.sqrt(DAYS)
    skew, kurt = stats.skew(r), stats.kurtosis(r, fisher=False)
    return float(stats.norm.cdf((sr - sr0) * np.sqrt(n - 1) / np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)))


def deflated_sharpe(r: pd.Series, trial_sharpes: list[float]) -> float:
    """PSR against the Sharpe expected from the best of N skill-less trials (Bailey & Lopez de Prado 2014)."""
    trials = [s for s in trial_sharpes if np.isfinite(s)]
    n = len(trials)
    if n < 2:
        return probabilistic_sharpe(r)
    sd = np.std(trials, ddof=1)
    z = (1 - EULER_GAMMA) * stats.norm.ppf(1 - 1 / n) + EULER_GAMMA * stats.norm.ppf(1 - 1 / (n * np.e))
    expected_max = sd * z
    return probabilistic_sharpe(r, expected_max)


def paired_sharpe_test(a: pd.Series, b: pd.Series, block: int = 21, n_boot: int = 2000, seed: int = 0):
    """Sharpe(a) - Sharpe(b), its 95% bootstrap interval and P(difference <= 0), using a paired circular
    block bootstrap of daily returns (keeps their correlation and autocorrelation)."""
    x = pd.concat([a, b], axis=1).dropna().to_numpy()
    t = len(x)
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = (rng.integers(0, t, -(-t // block))[:, None] + np.arange(block)).ravel()[:t] % t
        s = x[idx]
        sr = s.mean(0) / s.std(0, ddof=1) * np.sqrt(DAYS)
        diffs[i] = sr[0] - sr[1]
    observed = sharpe(pd.Series(x[:, 0])) - sharpe(pd.Series(x[:, 1]))
    return observed, tuple(np.quantile(diffs, [0.025, 0.975])), float((diffs <= 0).mean())
