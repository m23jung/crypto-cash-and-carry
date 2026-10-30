"""Analysis-ready panels: point-in-time universe and funding on a common 8-hour grid."""

from __future__ import annotations

import pandas as pd

from funding.sources import coin, multiplier

UNIVERSE_SIZE = 30


def symbol_map(symbols: list[str]) -> dict[str, str]:
    """coin -> symbol; if a venue lists a coin twice (re-denominated), keep the first alphabetically."""
    out: dict[str, str] = {}
    for s in sorted(symbols):
        out.setdefault(coin(s), s)
    return out


def monthly_universe(daily: pd.DataFrame, exclude: set[str], size: int = UNIVERSE_SIZE) -> pd.DataFrame:
    """Point-in-time membership: for each month, the top coins by trailing 30-day Binance volume among
    coins that traded on both venues on at least 25 of those 30 days. Uses only data before the month."""
    daily = daily[~daily["coin"].isin(exclude)]
    vol = daily.pivot_table(index="ts", columns=["venue", "coin"], values="quote_volume", aggfunc="sum")
    rows = []
    for month in pd.date_range("2021-01-01", pd.Timestamp.now(), freq="MS").tz_localize("UTC"):
        window = vol.loc[month - pd.Timedelta(days=30): month - pd.Timedelta(seconds=1)]
        both = (window["binance"].notna().sum() >= 25) & (window["bybit"].reindex(columns=window["binance"].columns)
                                                           .notna().sum() >= 25)
        top = window["binance"].loc[:, both].mean().nlargest(size)
        rows += [(month, c, rank) for rank, c in enumerate(top.index, 1)]
    return pd.DataFrame(rows, columns=["month", "coin", "rank"])


def to_8h(funding: pd.DataFrame, agg: str = "sum") -> pd.DataFrame:
    """Sum payments into 8-hour windows ending 00/08/16 UTC (window = (t-8h, t]), one column per venue/coin.

    Venues settle some coins every 1h or 4h; summing puts every coin on the same per-8h basis.
    A minute of tolerance absorbs exchange timestamps a few ms after the hour.
    """
    bucket = (funding["ts"] - pd.Timedelta(minutes=1)).dt.ceil("8h")
    return funding.assign(bucket=bucket).pivot_table(index="bucket", columns=["venue", "coin"], values="rate",
                                                     aggfunc=agg)  # agg="count" gives payments per window


def prices_8h(bars: pd.DataFrame, field: str = "close") -> pd.DataFrame:
    """8-hour bars (from Store.read("spot8h"/"perp8h")) -> one column per (venue, coin), in spot units.

    Perp prices are divided by the contract multiplier, so 1000PEPE and PEPE are comparable.
    """
    bars = bars.copy()
    if field == "close":
        bars["close"] = bars["close"] / bars["symbol"].map(multiplier)
    return bars.pivot_table(index="ts", columns=["venue", "coin"], values=field)


def basis(perp: pd.DataFrame, spot: pd.DataFrame) -> pd.DataFrame:
    """Perp premium over spot at each 8-hour close: perp / spot - 1 (positive = perp rich)."""
    perp, spot = perp.align(spot, join="inner")
    return perp / spot - 1
