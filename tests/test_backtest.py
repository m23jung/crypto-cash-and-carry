import numpy as np
import pandas as pd

from funding.backtest import Book, Costs, passive, run

N = 60


def _panel(perp_path=None, spot_path=None, funding=1e-4):
    idx = pd.date_range("2022-01-01", periods=N, freq="8h", tz="UTC")
    full = lambda v: pd.DataFrame({"A": v}, index=idx)  # noqa: E731
    spot = full(spot_path if spot_path is not None else np.full(N, 100.0))
    perp = full(perp_path if perp_path is not None else np.full(N, 100.0))
    return {"spot": spot, "perp": perp, "funding": full(np.full(N, funding)), "investable": full(np.full(N, True)),
            "spot_volume": full(np.full(N, 1e12)), "perp_volume": full(np.full(N, 1e12))}, idx


def _run(panel, idx, **kw):
    tbill = pd.Series(0.0, index=idx)
    start = idx[25]  # after the 7-day volume warm-up
    return run(panel, pd.Series(dtype=float), passive(("A",)), slots=1, capital=1.5e6, tbill=tbill,
               costs=Costs(), start=str(start), **kw)


def test_pure_carry_matches_hand_calculation():
    panel, idx = _panel()
    out = _run(panel, idx)
    q = 1e6 / 100  # 1.5M capital / 1.5 margin factor = 1M notional at price 100
    entry_cost = q * 100 * (0.0010 + 0.0002) + q * 100 * (0.0005 + 0.0002)
    windows_earning = len(out) - 2  # decided at the first window, entered at the second, earns from the third
    final = out["equity_start"].iloc[-1] + out["pnl"].iloc[-1]
    assert np.isclose(final, 1.5e6 - entry_cost + q * 100 * 1e-4 * windows_earning)
    parts = out[["funding", "basis", "unhedged", "cash"]].sum(axis=1) - out["costs"] - out["liquidation"]
    assert np.allclose(parts, out["pnl"])


def test_perp_richening_is_a_basis_loss_for_the_short():
    perp = np.full(N, 100.0)
    perp[40:] = 101.0  # perp rises 1% against flat spot
    panel, idx = _panel(perp_path=perp, funding=0.0)
    out = _run(panel, idx)
    assert np.isclose(out["basis"].sum(), -1e4 * 1.0)  # q = 10,000 coins x 1.0 widening


def test_spike_liquidates_the_short():
    path = np.full(N, 100.0)
    path[45:] = 150.0  # +50% in one window, above the 40% trigger
    panel, idx = _panel(perp_path=path, spot_path=path, funding=0.0)
    out = _run(panel, idx)
    hit = out.index[out["liquidation"] > 0]
    assert len(hit) == 1 and hit[0] == idx[45]
    assert np.isclose(out.loc[hit[0], "liquidation"], 1e4 * 150 * 0.02)
    assert out.loc[idx[45], "n_held"] == 0  # short gone at the spike
    assert out.loc[idx[46], "unhedged"] == 0  # leftover spot sold at a flat price: no extra P&L


def test_paired_sharpe_test_detects_a_better_series():
    from funding.metrics import paired_sharpe_test, probabilistic_sharpe

    rng = np.random.default_rng(1)
    noise = pd.Series(rng.normal(0, 0.01, 1500))
    good, bad = noise + 0.002, noise * 0.5 + rng.normal(0, 0.01, 1500) * 0.5
    diff, (lo, hi), p = paired_sharpe_test(good, bad)
    assert diff > 0 and lo > 0 and p < 0.05
    assert probabilistic_sharpe(good) > 0.99


def test_coin_without_a_perp_price_is_not_entered():
    perp = np.full(N, 100.0)
    perp[26:30] = np.nan  # perp missing exactly when the first order executes
    panel, idx = _panel(perp_path=perp)
    out = _run(panel, idx)
    assert np.isfinite(out["equity_start"]).all() and out.loc[idx[26]:idx[29], "n_held"].eq(0).all()


def test_joint_transfer_conserves_capital_and_arrives_next_day():
    from funding.backtest import run_joint

    panel, idx = _panel()
    panels = {"a": panel, "b": panel}
    sent = {"done": False}

    def decide(t, books, transit):  # move $100k from a to b once, hold nothing
        if sent["done"]:
            return {}, {}
        sent["done"] = True
        return {}, {("a", "b"): 100_000}

    out = run_joint(panels, decide, 1e6, pd.Series(0.0, index=idx), {"a": Costs(), "b": Costs()},
                    start=str(idx[25]))
    total = out["equity_start"] + out["pnl"]
    assert np.allclose(total.iloc[-1], 1e6 - 10.0)  # only the $10 transfer fee is lost
    moving = out.index[out["in_transit"] > 0]
    assert len(moving) == 3  # three 8-hour windows = one day in transit


def test_delisted_coin_is_closed_at_last_prices_after_three_days():
    path = np.full(N, 100.0)
    path[35:] = np.nan  # delisted: no prices from window 35 on
    panel, idx = _panel(perp_path=path, spot_path=path, funding=0.0)
    out = _run(panel, idx)
    assert out.loc[idx[35]:idx[43], "n_held"].eq(1).all()  # still held while within 3 days (9 windows)
    assert out.loc[idx[44]:, "n_held"].eq(0).all()  # then closed at the last prices
    assert np.isfinite(out["equity_start"]).all()


def test_hold_target_is_not_retraded_when_price_moves():
    path = np.full(N, 100.0)
    path[40:] = 110.0  # price rises 10% while the position is held
    panel, idx = _panel(perp_path=path, spot_path=path, funding=0.0)
    b = Book(panel, 1.5e6, Costs())
    for t in idx[25:]:
        b.begin(t, 0.0)
        if t == idx[30]:
            b.execute_notional({"A": 100_000.0})  # open
        elif t > idx[30]:
            b.execute_notional({"A": float("nan")})  # allocator says: hold
        b.finish(0.0)
    opens_and_resizes = [x for x in b.trades if x[3] in ("open", "resize")]
    assert len(opens_and_resizes) == 1  # only the initial open; no drift-chasing resize at 110
