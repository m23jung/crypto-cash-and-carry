import pandas as pd

from funding.milp import Params, solve

EQUITY, TBILL = 600_000, 0.042  # margin 1.5 -> $400k of notional


def _example():
    """The worked example: one venue, $600k, BTC and ETH already held at $150k each."""
    rows = [  # coin, forecast, x0, age_days
        ("BTC", 0.10, 150_000, 2000),
        ("ETH", 0.10, 150_000, 2000),
        ("SOL", 0.06, 0, 2000),
        ("DOGE", 0.22, 0, 2000),
        ("NEW", 0.60, 0, 40),
    ]
    c = pd.DataFrame(rows, columns=["coin", "forecast", "x0", "age_days"]).set_index("coin")
    return c.assign(margin=1.5, cost=0.0038, adv_cap=1e9)


def test_worked_example():
    x = solve(_example(), EQUITY, TBILL, Params())
    # BTC/ETH net (10% - 6.3% capital) x 30/365 = 0.30% < 0.38% cost: kept, but not topped up.
    assert x["BTC"] == 150_000 and x["ETH"] == 150_000
    assert x["SOL"] == 0  # 6% funding does not cover 1.5 x 4.2% T-bill
    assert round(x["DOGE"]) == 60_000  # 10% cap for non-majors
    assert round(x["NEW"]) == 30_000  # 5% cap for coins listed under 90 days


def test_no_trade_band_skips_small_resizes():
    c = _example()
    c.loc["BTC", ["forecast", "x0"]] = [0.30, 147_000]  # worth topping up the $3k to its 25% cap...
    assert round(solve(c, EQUITY, TBILL, Params())["BTC"]) == 150_000
    banded = solve(c, EQUITY, TBILL, Params(band_abs=5_000, band_rel=0.10))
    assert banded["BTC"] == 147_000  # ...but a $3k trade is inside the band: left alone


def test_exit_cost_blocks_marginal_rotation():
    c = _example()
    # Hold a weak coin; a slightly better one appears. Entry-only costing rotates, exit costing does not.
    c.loc["DOGE", ["forecast", "x0"]] = [0.12, 60_000]
    c.loc["NEW", ["forecast", "age_days"]] = [0.175, 2000]
    base = solve(c, EQUITY, TBILL, Params(max_positions=3))
    strict = solve(c, EQUITY, TBILL, Params(max_positions=3, exit_cost=True))
    assert base["DOGE"] == 0 and base["NEW"] > 0  # rotates out of DOGE
    assert strict["DOGE"] == 60_000  # exit fee makes the rotation not worth it
