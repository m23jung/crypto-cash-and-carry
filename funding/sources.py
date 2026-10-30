"""Downloaders for free data: Binance and Bybit USDT perps (daily volume, funding) and FRED.

Every function returns a plain DataFrame with millisecond ``ts``; caching lives in ``funding.store``.
"""

from __future__ import annotations

import contextlib
import io
import re
import signal
import time

import pandas as pd
import requests

START = pd.Timestamp("2020-12-01", tz="UTC")  # one month of volume history before the 2021 universe
STABLECOINS = {"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "USDE", "PYUSD"}

_session = requests.Session()
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (research script)"}  # Yahoo needs one; FRED rejects it, so per request


@contextlib.contextmanager
def _deadline(seconds: int):
    """Hard wall-clock limit on a blocking call (Unix, main thread)."""
    def expire(*_):
        raise TimeoutError(f"no complete response within {seconds}s")

    old = signal.signal(signal.SIGALRM, expire)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _backoff(attempt: int, why: str) -> None:
    """Exponential backoff, logged so a throttled download does not look frozen."""
    wait = 5 * 2**attempt
    print(f"  retry {attempt + 1}/6 after {why}: waiting {wait}s", flush=True)
    time.sleep(wait)


def _request(url: str, params: dict | None = None, pause: float = 0.0,
             headers: dict | None = None) -> requests.Response:
    """GET with backoff on rate limits (429/418), server errors and dropped connections."""
    for attempt in range(6):
        try:
            r = _session.get(url, params=params, timeout=30, headers=headers)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            _backoff(attempt, type(e).__name__)
            continue
        if r.status_code in (418, 429) or r.status_code >= 500:
            _backoff(attempt, f"HTTP {r.status_code}")
            continue
        r.raise_for_status()
        time.sleep(pause)
        return r
    raise RuntimeError(f"gave up on {url} {params} after 6 attempts")


def _get(url: str, params: dict | None = None, pause: float = 0.0):
    return _request(url, params, pause).json()


def _post(url: str, body: dict, pause: float = 0.0):
    """POST JSON with the same backoff as _request."""
    for attempt in range(6):
        try:
            with _deadline(60):  # the read timeout alone never fires if the server trickles bytes
                r = _session.post(url, json=body, timeout=30)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError,
                TimeoutError) as e:
            _backoff(attempt, type(e).__name__)
            continue
        if r.status_code in (418, 429) or r.status_code >= 500:
            _backoff(attempt, f"HTTP {r.status_code}")
            continue
        r.raise_for_status()
        time.sleep(pause)
        return r.json()
    raise RuntimeError(f"gave up on {url} {body} after 6 attempts")


def _ms(ts: pd.Timestamp) -> int:
    return int(ts.timestamp() * 1000)


# --- symbols ---------------------------------------------------------------


def coin(symbol: str) -> str:
    """Venue symbol -> coin, so venues can be matched: 1000PEPEUSDT, SHIB1000USDT, kPEPE (Hyperliquid)
    and PEPE-USD (dYdX) -> PEPE, SHIB."""
    base = symbol.removesuffix("USDT").removesuffix("-USD")
    base = re.sub(r"^k(?=[A-Z])", "", base)  # Hyperliquid's 1,000x contracts
    return re.sub(r"^(1000000|100000|10000|1000|1M)(?=[A-Z])|1000$", "", base)


def multiplier(symbol: str) -> int:
    """Coins per contract unit: 1000PEPEUSDT is quoted per 1,000 PEPE, so spot-equivalent price = price / 1000."""
    base = symbol.removesuffix("USDT")
    m = re.match(r"^(1000000|100000|10000|1000|1M)(?=[A-Z])", base) or re.search(r"(1000)$", base)
    if not m:
        return 1
    return 1_000_000 if m.group(1) == "1M" else int(m.group(1))


def _usdt_perps(symbols) -> list[str]:
    return sorted(s for s in set(symbols) if re.fullmatch(r"[A-Z0-9]+USDT", s) and coin(s) not in STABLECOINS)


def _s3_list(prefix: str, pattern: str) -> list[str]:
    """Matches of ``pattern`` in the data.binance.vision S3 listing under ``prefix`` (follows pagination)."""
    url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
    found, marker = [], ""
    while True:
        xml = _request(url, {"prefix": prefix, "delimiter": "/", "marker": marker}).text
        found += re.findall(pattern, xml)
        if "<IsTruncated>true" not in xml:
            return found
        marker = re.findall(r"<NextMarker>(.*?)</NextMarker>", xml)[-1]


def binance_symbols() -> list[str]:
    """Every Binance USD-M symbol ever archived (includes delisted)."""
    prefix = "data/futures/um/monthly/fundingRate/"
    return _usdt_perps(_s3_list(prefix, prefix + r"([A-Z0-9_]+)/"))


def _binance_archive(path: str, cols: list[int]) -> pd.DataFrame:
    """Monthly CSVs from data.binance.vision (``path`` under data/, e.g. "futures/um/monthly/fundingRate/X"),
    for delisted symbols the live API no longer serves."""
    prefix = f"data/{path}/"
    frames = [pd.read_csv(io.BytesIO(_request(f"https://data.binance.vision/{k}").content), compression="zip",
                          header=None, usecols=cols)
              for k in _s3_list(prefix, r"<Key>(" + re.escape(prefix) + r"[^<]+\.zip)</Key>")]
    if not frames:
        return pd.DataFrame(columns=cols)
    df = pd.concat(frames)
    df = df[pd.to_numeric(df[cols[0]], errors="coerce").notna()].astype(float)  # newer files have a header row
    return df[df[cols[0]] >= _ms(START)]


def _api_or_archive(fetch, archive):
    """Use the live API; fall back to the archive when Binance says the symbol no longer exists."""
    try:
        return fetch()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400 and "-1121" in e.response.text:
            return archive()
        raise


def tradfi_coins() -> set[str]:
    """Coins whose Binance perps all track a stock, ETF or commodity (contract type TRADIFI_PERPETUAL).

    ponytail: exchangeInfo only covers instruments still trading; a delisted TradFi perp would slip
    through. They only launched in 2025, so check the universe if that changes.
    """
    info = _get("https://fapi.binance.com/fapi/v1/exchangeInfo")["symbols"]
    is_tradfi = {x["symbol"]: x["contractType"] == "TRADIFI_PERPETUAL" or "TradFi" in x.get("underlyingSubType", [])
                 for x in info}
    tradfi = {coin(s) for s, t in is_tradfi.items() if t}
    crypto = {coin(s) for s, t in is_tradfi.items() if not t}
    return tradfi - crypto  # a ticker can be both (CAT: Caterpillar and a meme coin); keep the crypto one


def bybit_symbols() -> list[str]:
    """Every Bybit linear symbol with a public trade archive (includes delisted)."""
    html = _request("https://public.bybit.com/trading/").text
    return _usdt_perps(re.findall(r'href="([A-Z0-9]+)/"', html))


# --- fetchers ----------------------------------------------------------------


def binance_daily(symbol: str) -> pd.DataFrame:
    return _api_or_archive(lambda: _binance_daily_api(symbol), lambda: _binance_archive(
        f"futures/um/monthly/klines/{symbol}/1d", [0, 4, 7])
        .set_axis(["ts", "close", "quote_volume"], axis=1).astype({"ts": "int64"}))


def _binance_daily_api(symbol: str) -> pd.DataFrame:
    rows, start = [], _ms(START)
    while True:
        batch = _get("https://fapi.binance.com/fapi/v1/klines",
                     {"symbol": symbol, "interval": "1d", "startTime": start, "limit": 1500}, pause=0.3)
        rows += batch
        if len(batch) < 1500:
            break
        start = batch[-1][0] + 1
    df = pd.DataFrame([(r[0], float(r[4]), float(r[7])) for r in rows], columns=["ts", "close", "quote_volume"])
    return df


def bybit_daily(symbol: str) -> pd.DataFrame:
    rows, start, now = [], _ms(START), _ms(pd.Timestamp.now(tz="UTC"))
    step = 1000 * 86_400_000
    while start < now:
        res = _get("https://api.bybit.com/v5/market/kline",
                   {"category": "linear", "symbol": symbol, "interval": "D", "start": start,
                    "end": start + step - 1, "limit": 1000}, pause=0.05)
        if res["retCode"]:  # symbol unknown to the API: treat as no data
            print(f"  bybit {symbol}: {res['retMsg']}")
            break
        rows += res["result"]["list"]
        start += step
    df = pd.DataFrame([(int(r[0]), float(r[4]), float(r[6])) for r in rows], columns=["ts", "close", "quote_volume"])
    return df.drop_duplicates("ts")


def binance_funding(symbol: str) -> pd.DataFrame:
    return _api_or_archive(lambda: _binance_funding_api(symbol), lambda: _binance_archive(
        f"futures/um/monthly/fundingRate/{symbol}", [0, 2]).set_axis(["ts", "rate"], axis=1).astype({"ts": "int64"}))


def _binance_funding_api(symbol: str) -> pd.DataFrame:
    rows, start = [], _ms(START)
    while True:
        batch = _get("https://fapi.binance.com/fapi/v1/fundingRate",
                     {"symbol": symbol, "startTime": start, "limit": 1000}, pause=0.65)
        rows += batch
        if len(batch) < 1000:
            break
        start = batch[-1]["fundingTime"] + 1
    return pd.DataFrame([(r["fundingTime"], float(r["fundingRate"])) for r in rows], columns=["ts", "rate"])


def bybit_funding(symbol: str) -> pd.DataFrame:
    rows, end = [], _ms(pd.Timestamp.now(tz="UTC"))
    while True:
        res = _get("https://api.bybit.com/v5/market/funding/history",
                   {"category": "linear", "symbol": symbol, "endTime": end, "limit": 200}, pause=0.05)
        if res["retCode"]:
            print(f"  bybit {symbol}: {res['retMsg']}")
            break
        batch = res["result"]["list"]  # newest first
        rows += batch
        if len(batch) < 200 or int(batch[-1]["fundingRateTimestamp"]) < _ms(START):
            break
        end = int(batch[-1]["fundingRateTimestamp"]) - 1
    df = pd.DataFrame([(int(r["fundingRateTimestamp"]), float(r["fundingRate"])) for r in rows], columns=["ts", "rate"])
    return df[df["ts"] >= _ms(START)].drop_duplicates("ts")


def hyperliquid_symbols() -> list[str]:
    """Every Hyperliquid perp, including delisted ones."""
    return [x["name"] for x in _post("https://api.hyperliquid.xyz/info", {"type": "meta"})["universe"]]


def hyperliquid_funding(name: str) -> pd.DataFrame:
    """Hourly funding, 500 rows per call; paged forward from START."""
    rows, start = [], _ms(START)
    while True:
        batch = _post("https://api.hyperliquid.xyz/info", {"type": "fundingHistory", "coin": name, "startTime": start},
                      pause=2.0)  # heavy endpoint: stay well under the 1,200-weight-per-minute limit
        rows += batch
        if len(batch) < 500:
            break
        start = batch[-1]["time"] + 1
    return pd.DataFrame([(int(x["time"]), float(x["fundingRate"])) for x in rows], columns=["ts", "rate"])


def dydx_symbols() -> list[str]:
    return list(_get("https://indexer.dydx.trade/v4/perpetualMarkets")["markets"])


def dydx_funding(ticker: str) -> pd.DataFrame:
    """Hourly funding from the dYdX v4 indexer, 1,000 rows per call; paged backward."""
    rows, before = [], None
    while True:
        params = {"limit": 1000, **({"effectiveBeforeOrAt": before} if before else {})}
        url = f"https://indexer.dydx.trade/v4/historicalFunding/{ticker}"
        batch = _get(url, params, pause=0.2)["historicalFunding"]
        rows += batch
        if len(batch) < 1000:
            break
        oldest = pd.Timestamp(batch[-1]["effectiveAt"]) - pd.Timedelta(milliseconds=1)
        before = oldest.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    df = pd.DataFrame([(_ms(pd.Timestamp(x["effectiveAt"])), float(x["rate"])) for x in rows], columns=["ts", "rate"])
    return df.drop_duplicates("ts")


EIGHT_HOURS_MS = 8 * 3_600_000
_BINANCE_KLINES = {"spot": ("https://api.binance.com/api/v3/klines", 1000, "spot/monthly/klines"),
                   "perp": ("https://fapi.binance.com/fapi/v1/klines", 1500, "futures/um/monthly/klines")}


def binance_8h(symbol: str, market: str) -> pd.DataFrame:
    """8-hour bars (ts = bar close time, close, quote_volume) for Binance spot or USD-M perp."""
    url, limit, archive = _BINANCE_KLINES[market]

    def api():
        rows, start = [], _ms(START)
        while True:
            batch = _get(url, {"symbol": symbol, "interval": "8h", "startTime": start, "limit": limit}, pause=0.2)
            rows += batch
            if len(batch) < limit:
                break
            start = batch[-1][0] + 1
        return pd.DataFrame([(r[0], float(r[4]), float(r[7])) for r in rows], columns=["ts", "close", "quote_volume"])

    df = _api_or_archive(api, lambda: _binance_archive(f"{archive}/{symbol}/8h", [0, 4, 7]).set_axis(
        ["ts", "close", "quote_volume"], axis=1).astype({"ts": "int64"}))
    df = df.assign(ts=df["ts"] + EIGHT_HOURS_MS)  # open time -> close time
    return df[df["ts"] <= _ms(pd.Timestamp.now(tz="UTC"))]  # drop the bar still forming


def bybit_8h(symbol: str, market: str) -> pd.DataFrame:
    """8-hour bars for Bybit spot or linear perp, built from 4-hour bars (Bybit has no 8h interval).

    Only 8-hour windows with both 4-hour bars are kept.
    """
    category = {"spot": "spot", "perp": "linear"}[market]
    rows, start, now = [], _ms(START), _ms(pd.Timestamp.now(tz="UTC"))
    step = 1000 * 4 * 3_600_000
    while start < now:
        res = _get("https://api.bybit.com/v5/market/kline",
                   {"category": category, "symbol": symbol, "interval": "240", "start": start,
                    "end": start + step - 1, "limit": 1000}, pause=0.05)
        if res["retCode"]:
            print(f"  bybit {market} {symbol}: {res['retMsg']}")
            break
        rows += res["result"]["list"]
        start += step
    bars = pd.DataFrame([(int(r[0]), float(r[4]), float(r[6])) for r in rows],
                        columns=["open_ts", "close", "quote_volume"]).drop_duplicates("open_ts").sort_values("open_ts")
    window = bars["open_ts"] // EIGHT_HOURS_MS * EIGHT_HOURS_MS + EIGHT_HOURS_MS  # close time of the 8h window
    g = bars.groupby(window)
    out = pd.DataFrame({"close": g["close"].last(), "quote_volume": g["quote_volume"].sum(), "n": g.size()})
    out = out[(out["n"] == 2) & (out.index <= now)]  # complete windows only
    return out.drop(columns="n").rename_axis("ts").reset_index()


def fred(series: str) -> pd.Series:
    text = _request("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series}).text
    df = pd.read_csv(io.StringIO(text), index_col=0, parse_dates=True, na_values=".")
    return df.iloc[:, 0].dropna().rename(series)


def yahoo_daily(ticker: str) -> tuple[pd.Series, str]:
    """Daily closes (indexed by trading date) and Yahoo's instrument type (EQUITY, ETF, FUTURE...)."""
    res = _request(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", {"range": "5y", "interval": "1d"},
                   pause=0.3, headers=YAHOO_HEADERS).json()["chart"]["result"][0]
    dates = pd.to_datetime(res["timestamp"], unit="s").normalize()
    close = pd.Series(res["indicators"]["quote"][0]["close"], index=dates, name=ticker, dtype=float).dropna()
    return close[~close.index.duplicated(keep="last")], res["meta"].get("instrumentType", "")


FETCH = {
    ("binance", "daily"): binance_daily,
    ("bybit", "daily"): bybit_daily,
    ("binance", "funding"): binance_funding,
    ("bybit", "funding"): bybit_funding,
    ("binance", "spot8h"): lambda s: binance_8h(s, "spot"),
    ("binance", "perp8h"): lambda s: binance_8h(s, "perp"),
    ("bybit", "spot8h"): lambda s: bybit_8h(s, "spot"),
    ("hyperliquid", "funding"): hyperliquid_funding,
    ("dydx", "funding"): dydx_funding,
    ("bybit", "perp8h"): lambda s: bybit_8h(s, "perp"),
}
