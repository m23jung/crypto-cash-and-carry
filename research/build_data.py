"""Build the local database: symbol lists, daily volume, universe, funding history, 8-hour spot and perp bars.

Run:  python research/build_data.py [binance|bybit]
Resumable: cached symbols are skipped. Pass a venue to download one venue only, so two can run in parallel.
"""

import sys

from funding.panels import UNIVERSE_SIZE, monthly_universe, symbol_map
from funding.sources import binance_symbols, bybit_symbols, tradfi_coins
from funding.store import Store


def build(venues: tuple[str, ...] = ("binance", "bybit"), store: Store | None = None) -> None:
    store = store or Store()
    perps = {"binance": symbol_map(binance_symbols()), "bybit": symbol_map(bybit_symbols())}
    common = sorted(set(perps["binance"]) & set(perps["bybit"]))
    print(f"{len(perps['binance'])} Binance and {len(perps['bybit'])} Bybit USDT perps ever listed; "
          f"{len(common)} coins on both")
    for v in venues:
        store.ensure(v, "daily", [perps[v][c] for c in common])
    members = sorted(set(monthly_universe(store.read("daily"), tradfi_coins())["coin"]))
    print(f"{len(members)} coins were ever in the monthly top {UNIVERSE_SIZE}")
    for v in venues:
        store.ensure(v, "funding", [perps[v][c] for c in members])
        store.ensure(v, "perp8h", [perps[v][c] for c in members])
        # Spot trades under the plain coin name (PEPEUSDT, not 1000PEPEUSDT); no listing means no spot leg.
        store.ensure(v, "spot8h", [f"{c}USDT" for c in members])


if __name__ == "__main__":
    build(tuple(sys.argv[1:]) or ("binance", "bybit"))
