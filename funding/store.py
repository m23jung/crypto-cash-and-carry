"""SQLite cache: download once, read many times."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from funding.sources import FETCH, coin

DB_PATH = Path("data/funding.db")


class Store:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=30)  # tolerate a second downloader writing
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily (venue TEXT, symbol TEXT, ts INTEGER, close REAL, quote_volume REAL,
                                              PRIMARY KEY (venue, symbol, ts));
            CREATE TABLE IF NOT EXISTS funding (venue TEXT, symbol TEXT, ts INTEGER, rate REAL,
                                                PRIMARY KEY (venue, symbol, ts));
            CREATE TABLE IF NOT EXISTS spot8h (venue TEXT, symbol TEXT, ts INTEGER, close REAL, quote_volume REAL,
                                               PRIMARY KEY (venue, symbol, ts));
            CREATE TABLE IF NOT EXISTS perp8h (venue TEXT, symbol TEXT, ts INTEGER, close REAL, quote_volume REAL,
                                               PRIMARY KEY (venue, symbol, ts));
            CREATE TABLE IF NOT EXISTS fetched (venue TEXT, kind TEXT, symbol TEXT, PRIMARY KEY (venue, kind, symbol));
        """)

    def ensure(self, venue: str, kind: str, symbols: list[str]) -> None:
        """Download anything not yet cached. ponytail: no incremental top-up; delete the DB to refresh."""
        done = {s for (s,) in self.conn.execute("SELECT symbol FROM fetched WHERE venue=? AND kind=?", (venue, kind))}
        todo = [s for s in symbols if s not in done]
        for i, s in enumerate(todo, 1):
            key = (venue, kind, s)
            if self.conn.execute("SELECT 1 FROM fetched WHERE venue=? AND kind=? AND symbol=?", key).fetchone():
                continue  # fetched meanwhile by another process
            df = FETCH[venue, kind](s).assign(venue=venue, symbol=s)
            with self.conn:
                df.to_sql(kind, self.conn, if_exists="append", index=False, method="multi", chunksize=500)
                self.conn.execute("INSERT INTO fetched VALUES (?, ?, ?)", (venue, kind, s))
            print(f"  {venue} {kind} {i}/{len(todo)} {s}: {len(df)} rows", flush=True)

    def read(self, kind: str) -> pd.DataFrame:
        df = pd.read_sql(f"SELECT * FROM {kind}", self.conn)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df["coin"] = df["symbol"].map(coin)
        return df
