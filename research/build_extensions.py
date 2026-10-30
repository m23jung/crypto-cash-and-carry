"""Download data for the optional extensions (no analysis here).

  python research/build_extensions.py hyperliquid   # hourly funding, universe coins listed there (incl. delisted)
  python research/build_extensions.py dydx          # hourly funding, universe coins listed there
  python research/build_extensions.py tradfi        # stock/commodity perps on Binance and Bybit: funding + 8h prices

Resumable: cached symbols are skipped. Each venue can run in its own process.
"""

import sys

from funding.panels import monthly_universe, symbol_map
from funding.sources import _get, _usdt_perps, bybit_symbols, coin, dydx_symbols, hyperliquid_symbols, tradfi_coins
from funding.store import Store


def main(which: str) -> None:
    store = Store()
    if which in ("hyperliquid", "dydx"):
        members = set(monthly_universe(store.read("daily"), tradfi_coins())["coin"])
        listed = symbol_map(hyperliquid_symbols() if which == "hyperliquid" else dydx_symbols())
        todo = [listed[c] for c in sorted(members & set(listed))]
        print(f"{which}: {len(todo)} of {len(members)} universe coins listed", flush=True)
        store.ensure(which, "funding", todo)
    elif which == "tradfi":
        info = _get("https://fapi.binance.com/fapi/v1/exchangeInfo")["symbols"]
        binance = _usdt_perps(x["symbol"] for x in info if x["contractType"] == "TRADIFI_PERPETUAL"
                              or "TradFi" in x.get("underlyingSubType", []))
        coins = {coin(s) for s in binance}
        bybit = [s for s in bybit_symbols() if coin(s) in coins]
        print(f"tradfi: {len(binance)} Binance and {len(bybit)} Bybit perps", flush=True)
        for venue, symbols in [("binance", binance), ("bybit", bybit)]:
            store.ensure(venue, "funding", symbols)
            store.ensure(venue, "perp8h", symbols)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
