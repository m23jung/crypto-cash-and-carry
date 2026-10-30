import pandas as pd

from funding.panels import to_8h
from funding.sources import coin


def test_coin_matches_across_venues():
    assert coin("1000PEPEUSDT") == coin("PEPEUSDT") == "PEPE"
    assert coin("SHIB1000USDT") == coin("1000SHIBUSDT") == "SHIB"
    assert coin("1000000MOGUSDT") == "MOG"
    assert coin("1INCHUSDT") == "1INCH"  # leading digit that is part of the name
    assert coin("kPEPE") == coin("PEPE-USD") == "PEPE"  # Hyperliquid and dYdX naming
    assert coin("BTC-USD") == coin("BTC") == "BTC"


def test_to_8h_sums_any_interval_into_same_window():
    ts = pd.to_datetime(
        ["2024-01-01 00:00:00.003",  # 8h payment stamped just after midnight -> window ending 00:00
         "2024-01-01 04:00:00.000", "2024-01-01 08:00:00.000",  # 4h payments -> both in window ending 08:00
         "2024-01-01 09:00:00.000"],  # hourly payment -> window ending 16:00
        utc=True)
    f = pd.DataFrame({"ts": ts, "rate": [1.0, 2.0, 3.0, 4.0], "venue": "x", "coin": "C"})
    out = to_8h(f)[("x", "C")]
    assert out.to_dict() == {pd.Timestamp("2024-01-01 00:00", tz="UTC"): 1.0,
                             pd.Timestamp("2024-01-01 08:00", tz="UTC"): 5.0,
                             pd.Timestamp("2024-01-01 16:00", tz="UTC"): 4.0}


def test_multiplier_matches_contract_size():
    from funding.sources import multiplier

    assert multiplier("1000PEPEUSDT") == multiplier("SHIB1000USDT") == 1000
    assert multiplier("1000000MOGUSDT") == multiplier("1MBABYDOGEUSDT") == 1_000_000
    assert multiplier("BTCUSDT") == multiplier("1INCHUSDT") == 1
