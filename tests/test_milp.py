import pandas as pd

from funding.milp import Params, solve


def _example():
    """The worked example: $1M NAV, $500k per venue, BTC and ETH already held on Binance."""
    rows = [  # venue, coin, forecast, x0, age_days
        ("binance", "BTC", 0.1095, 150_000, 2000),
        ("binance", "ETH", 0.100, 150_000, 2000),
        ("binance", "SOL", 0.14, 0, 2000),
        ("bybit", "BTC", 0.06, 0, 2000),
        ("bybit", "DOGE", 0.22, 0, 2000),
        ("bybit", "NEW", 0.60, 0, 40),
    ]
    c = pd.DataFrame(rows, columns=["venue", "coin", "forecast", "x0", "age_days"]).set_index(["venue", "coin"])
    return c.assign(margin=1.5, cost=0.0038, adv_cap=1e9)


def test_worked_example():
    x, transfers = solve(_example(), {"binance": 500_000, "bybit": 500_000}, {}, 1_000_000, 0.042, Params())
    assert x[("binance", "BTC")] == 150_000 and x[("binance", "ETH")] == 150_000  # kept, no rotation
    assert x[("bybit", "BTC")] == 0  # 6% funding does not cover 1.5 x 4.2% T-bill
    assert round(x[("bybit", "DOGE")]) == 50_000  # 10% cap for non-majors
    assert round(x[("bybit", "NEW")]) == 25_000  # 5% cap for coins listed under 90 days
    # SOL nets (14% - 6.3% capital - 3% penalty) x 30/365 - 0.38% cost = +0.006%: worth opening with the
    # $33k of Binance capital left, but the extra $17k up to its cap earns ~$1, less than a transfer.
    assert round(x[("binance", "SOL")]) == 33_333 and transfers == {}


def test_transfer_when_the_extra_carry_pays_for_it():
    c = _example()
    c.loc[("binance", "SOL"), "forecast"] = 0.30  # now the extra $17k of SOL earns ~$220 over 30 days
    x, transfers = solve(c, {"binance": 500_000, "bybit": 500_000}, {}, 1_000_000, 0.042, Params())
    assert round(x[("binance", "SOL")]) == 50_000  # filled to its 10% cap
    assert transfers == {("bybit", "binance"): 50_000}  # minimum transfer from idle Bybit capital


def test_fixed_split_ablation_makes_no_transfer():
    x, transfers = solve(_example(), {"binance": 500_000, "bybit": 500_000}, {}, 1_000_000, 0.042,
                         Params(transfers=False))
    assert transfers == {}


def test_no_trade_band_skips_small_resizes():
    c = _example()
    c.loc[("binance", "BTC"), "x0"] = 147_000  # drifted $3k below where the capital constraint would allow
    x, _ = solve(c, {"binance": 500_000, "bybit": 500_000}, {}, 1_000_000, 0.042,
                 Params(band_abs=5_000, band_rel=0.10))
    assert x[("binance", "BTC")] == 147_000  # a $3k top-up is inside the band: left alone


def test_exit_cost_blocks_marginal_rotation():
    c = _example()
    # Hold a weak coin; a slightly better one appears. Entry-only costing rotates, exit costing does not.
    c.loc[("bybit", "DOGE"), ["forecast", "x0"]] = [0.12, 50_000]
    c.loc[("bybit", "NEW"), ["forecast", "age_days"]] = [0.175, 2000]
    eq = {"binance": 500_000, "bybit": 500_000}
    base, _ = solve(c, eq, {}, 1_000_000, 0.042, Params(max_positions=3, transfers=False))
    strict, _ = solve(c, eq, {}, 1_000_000, 0.042, Params(max_positions=3, transfers=False, exit_cost=True))
    assert base[("bybit", "DOGE")] == 0 and base[("bybit", "NEW")] > 0  # rotates out of DOGE
    assert strict[("bybit", "DOGE")] == 50_000  # exit fee makes the rotation not worth it
