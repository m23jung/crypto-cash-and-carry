import numpy as np
import pandas as pd
import pytest

from funding.forecast import features, forward_mean, walk_forward


def _panel(seed=0, start="2021-01-01", periods=3 * 365 * 2):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=periods, freq="8h", tz="UTC")
    f = pd.DataFrame(1e-4 + 2e-4 * rng.standard_normal((periods, 4)).cumsum(0) / 50, index=idx,
                     columns=list("ABCD"))
    b = pd.DataFrame(1e-3 * rng.standard_normal((periods, 4)), index=idx, columns=list("ABCD"))
    return f, b


def test_forward_mean_uses_only_the_next_windows():
    f = pd.DataFrame({"A": [1.0, 2.0, 3.0, 4.0, 5.0]})
    assert forward_mean(f, 2)["A"].tolist()[:3] == [2.5, 3.5, 4.5]
    assert forward_mean(f, 2)["A"].iloc[3:].isna().all()


@pytest.mark.parametrize("target", ["target_7d", "target_30d"])
def test_walk_forward_forecasts_ignore_the_future(target):
    f, b = _panel()
    cut = pd.Timestamp("2022-06-01", tz="UTC")
    base = walk_forward(features(f, b), target=target)
    scrambled = f.copy()
    scrambled.loc[scrambled.index > cut] *= -50  # wildly different future
    after = walk_forward(features(scrambled, b), target=target)
    models = ["M1_last", "M2_ewma", "M3_regression"]
    before_cut = base.index.get_level_values("ts") <= cut
    pd.testing.assert_frame_equal(base.loc[before_cut, models], after.loc[before_cut, models])
