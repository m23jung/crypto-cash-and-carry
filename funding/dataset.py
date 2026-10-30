"""Venue panels shared by Phases 2-4: funding, prices, basis, volume and the investable set."""

from __future__ import annotations

import pandas as pd

from funding.forecast import features
from funding.panels import basis, monthly_universe, prices_8h, to_8h
from funding.sources import fred, tradfi_coins
from funding.store import Store

VENUES = ("binance", "bybit")
MAX_ABS_BASIS = 0.20  # beyond this a print is a collapse or a broken spot/perp pair, not a basis trade
PER_YEAR = 3 * 365


def member_mask(universe: pd.DataFrame, index: pd.DatetimeIndex, coins) -> pd.DataFrame:
    """True where the coin is in that month's universe (a window ending 00:00 on the 1st is last month's)."""
    month = (index - pd.Timedelta(minutes=1)).tz_localize(None).to_period("M")
    mask = pd.DataFrame(False, index=index, columns=coins)
    for m, cs in universe.groupby(universe["month"].dt.tz_localize(None).dt.to_period("M"))["coin"]:
        mask.loc[month == m, mask.columns.intersection(cs)] = True
    return mask


def load():
    """Per venue: funding, spot/perp prices (spot units), basis, 8h volume and the investable mask."""
    store = Store()
    universe = monthly_universe(store.read("daily"), tradfi_coins())
    funding = to_8h(store.read("funding")).loc["2021-01-01":]
    funding = funding.loc[:core_end(funding)]
    spot_bars, perp_bars = store.read("spot8h"), store.read("perp8h")
    spot, perp = prices_8h(spot_bars), prices_8h(perp_bars)
    spot_vol, perp_vol = prices_8h(spot_bars, "quote_volume"), prices_8h(perp_bars, "quote_volume")
    panels = {}
    for v in VENUES:
        f = funding[v]
        b = basis(perp[v], spot[v]).reindex(index=f.index, columns=f.columns)
        member = member_mask(universe, f.index, f.columns)
        has_spot = spot[v].reindex(index=f.index, columns=f.columns).notna()
        broken = b.abs() > MAX_ABS_BASIS
        investable = member & has_spot & f.notna() & ~broken
        grid = {"index": f.index, "columns": f.columns}
        panels[v] = {"funding": f, "basis": b, "member": member, "has_spot": has_spot, "broken": broken,
                     "investable": investable, "spot": spot[v].reindex(**grid), "perp": perp[v].reindex(**grid),
                     "spot_volume": spot_vol[v].reindex(**grid), "perp_volume": perp_vol[v].reindex(**grid)}
    return panels


def investable_rows(p: dict) -> pd.DataFrame:
    """Feature rows for investable coin-windows only. Targets use the coin's full funding history,
    so a position entered while investable keeps earning after the coin leaves the universe."""
    feats = features(p["funding"], p["basis"])
    keep = p["investable"].stack().reindex(feats.index, fill_value=False)
    return feats[keep.to_numpy()]




def core_end(funding: pd.DataFrame) -> pd.Timestamp:
    """Last window with BTC funding on every core venue, so later-downloaded extension data
    (other venues, TradFi perps) cannot stretch the core panels."""
    return min(funding[v]["BTC"].last_valid_index() for v in VENUES)


def tbill_8h(index: pd.DatetimeIndex) -> pd.Series:
    """3-month T-bill per 8-hour window (fraction), using the previous day's print."""
    t = (fred("DGS3MO") / 100 / PER_YEAR).tz_localize("UTC")
    return t.reindex(t.index.union(index)).ffill().shift(1).reindex(index)
