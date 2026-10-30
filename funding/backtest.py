"""Spot/perp funding-carry backtest on the 8-hour grid. Spec: docs/plan.md, "Phase 3 spec".

One book per venue. A position is q coins long spot and q coins short the perp (spot units). Each
window's P&L is split into funding, basis, trading costs, liquidation penalties and cash interest;
the parts sum to the change in equity exactly (checked in tests).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

WINDOWS_PER_DAY = 3
HORIZON = 21  # 7-day forecast horizon, in 8-hour windows
STALE_EXIT = pd.Timedelta(days=3)  # a held coin with no price this long (delisted) is closed at its last prices


@dataclass(frozen=True)
class Costs:
    spot_fee: float = 0.0010  # taker, both venues
    perp_fee: float = 0.0005  # taker; Bybit 0.00055
    slippage: float = 0.0002  # per leg
    margin_buffer: float = 0.50  # short-perp margin as a share of notional (no cross-margin)
    liquidation_rise: float = 0.40  # perp close up this much since the last daily top-up -> liquidated
    liquidation_penalty: float = 0.02  # share of perp notional
    adv_cap: float = 0.01  # max position notional / trailing 7-day average daily volume
    borrow_rate: float | None = None  # annual rate on negative cash (borrowed to lever up); None = T-bill

    @property
    def round_trip(self) -> float:
        return 2 * (self.spot_fee + self.perp_fee + 2 * self.slippage)


# A rule sees (t, held coins, investable coins, forecasts at t, T-bill at t) and returns the coins to hold.
Rule = Callable[[pd.Timestamp, set, list, pd.Series, float], set]


def passive(coins: tuple[str, ...]) -> Rule:
    """S1: always hold the given coins when investable."""
    return lambda t, held, inv, fc, tb: set(coins) & set(inv)


def naive_top_k(k: int, every: int = HORIZON) -> Rule:
    """S2: rotate into the top-k forecasts every ``every`` windows, ignoring costs."""
    state = {"i": 0}

    def rule(t, held, inv, fc, tb):
        state["i"] += 1
        if (state["i"] - 1) % every:
            return held & set(inv)
        return set(fc.reindex(inv).dropna().nlargest(k).index)

    return rule


def cost_aware_top_k(k: int, costs: Costs) -> Rule:
    """S3: enter when forecast funding beats T-bill plus amortised round-trip cost; exit below T-bill."""

    def rule(t, held, inv, fc, tb):
        f = fc.reindex(inv).dropna()
        keep = {c for c in held if c in f.index and f[c] >= tb}
        hurdle = tb + costs.round_trip / HORIZON
        new = f[(f > hurdle) & ~f.index.isin(keep)].nlargest(max(k - len(keep), 0))
        return keep | set(new.index)

    return rule


class Book:
    """One venue's carry book: positions, cash and the per-window ledger.

    ``margin`` maps a coin to its capital factor (capital tied up per $1 of notional); default
    1 + costs.margin_buffer for every coin.
    """

    def __init__(self, panel: dict, capital: float, costs: Costs, margin: Callable[[str], float] | None = None,
                 name: str = ""):
        self.spot, self.perp, self.funding = panel["spot"], panel["perp"], panel["funding"]
        self.inv_mask = panel["investable"]
        vol = panel["spot_volume"].combine(panel["perp_volume"], np.fmin)
        self.adv = vol.rolling(HORIZON, min_periods=HORIZON).sum() / 7
        self.costs, self.equity = costs, capital
        self.margin = margin or (lambda c: 1 + costs.margin_buffer)
        self.q: dict[str, float] = {}  # coins held
        self.ref: dict[str, float] = {}  # perp price at the last daily margin top-up
        self.last_s: dict[str, float] = {}
        self.last_p: dict[str, float] = {}
        self.unhedged: dict[str, float] = {}  # spot left after a liquidation, sold next window
        self.name, self.trades = name, []  # trade log: (ts, venue, coin, kind, notional)
        self.unpriced_since: dict[str, pd.Timestamp] = {}

    def _priced(self, c) -> bool:
        return np.isfinite(self.s_t.get(c, np.nan)) and np.isfinite(self.p_t.get(c, np.nan))

    def notional(self, c) -> float:
        return self.q[c] * self.last_s[c]

    def deployed(self) -> float:
        return sum(self.q[c] * self.last_s[c] * self.margin(c) for c in self.q)

    def begin(self, t, tbill_t: float) -> None:
        """Steps 1-2: carry over (t-1, t], then liquidations, forced exits and the daily margin top-up."""
        self.t, self.s_t, self.p_t = t, self.spot.loc[t], self.perp.loc[t]
        f_t, costs = self.funding.loc[t], self.costs
        self.rec = rec = dict.fromkeys(["funding", "basis", "unhedged", "costs", "liquidation", "cash", "traded"], 0.0)
        idle = self.equity - self.deployed() - sum(self.unhedged[c] * self.last_s[c] for c in self.unhedged)
        rate = tbill_t if idle >= 0 or costs.borrow_rate is None else costs.borrow_rate / (3 * 365)
        rec["cash"] = idle * rate
        for c in list(self.q):
            if self._priced(c):
                s, p = self.s_t[c], self.p_t[c]
                rec["funding"] += self.q[c] * p * (f_t.get(c, 0.0) if np.isfinite(f_t.get(c, np.nan)) else 0.0)
                rec["basis"] -= self.q[c] * ((p - s) - (self.last_p[c] - self.last_s[c]))
                self.last_s[c], self.last_p[c] = s, p
        for c in list(self.q):  # delisted or long-unpriced: close at the last known prices
            if self._priced(c):
                self.unpriced_since.pop(c, None)
            elif t - self.unpriced_since.setdefault(c, t) >= STALE_EXIT:
                self.close(c, self.last_s[c], self.last_p[c], kind="stale close")
                self.unpriced_since.pop(c)
        for c in list(self.unhedged):
            if not np.isfinite(self.s_t.get(c, np.nan)) and t - self.unpriced_since.setdefault(c, t) >= STALE_EXIT:
                rec["costs"] += self.unhedged[c] * self.last_s[c] * (costs.spot_fee + costs.slippage)
                rec["traded"] += self.unhedged[c] * self.last_s[c]
                del self.unhedged[c], self.unpriced_since[c]
            elif np.isfinite(self.s_t.get(c, np.nan)):
                self.unpriced_since.pop(c, None)
                rec["unhedged"] += self.unhedged[c] * (self.s_t[c] - self.last_s[c])
                rec["costs"] += self.unhedged[c] * self.s_t[c] * (costs.spot_fee + costs.slippage)
                rec["traded"] += self.unhedged[c] * self.s_t[c]
                del self.unhedged[c]

        self.inv = [c for c in self.inv_mask.columns[self.inv_mask.loc[t].to_numpy()]]
        self.blocked = set()  # exited by force at t: not re-entered until the rule decides again
        for c in list(self.q):
            if c in self.ref and np.isfinite(self.p_t.get(c, np.nan)) and \
                    self.p_t[c] / self.ref[c] - 1 > costs.liquidation_rise:
                rec["liquidation"] += self.q[c] * self.p_t[c] * costs.liquidation_penalty
                self.trades.append((t, self.name, c, "liquidation", self.q[c] * self.p_t[c]))
                self.unhedged[c] = self.q.pop(c)
                self.ref.pop(c)
                self.blocked.add(c)
            elif c not in self.inv and self._priced(c):
                self.close(c)
                self.blocked.add(c)
        if t.hour == 0:
            self.ref.update({c: self.p_t[c] for c in self.q if np.isfinite(self.p_t.get(c, np.nan))})

    def close(self, c, s: float | None = None, p: float | None = None, kind: str = "close") -> None:
        s = self.s_t[c] if s is None else s
        p = self.p_t[c] if p is None else p
        self.trades.append((self.t, self.name, c, kind, self.q[c] * s))
        self.rec["costs"] += _trade_cost(self.q[c], s, p, self.costs)
        self.rec["traded"] += self.q[c] * s
        self.q.pop(c), self.ref.pop(c, None)

    def open(self, c, notional: float) -> None:
        self.trades.append((self.t, self.name, c, "open", notional))
        s, p = self.s_t[c], self.p_t[c]
        self.q[c] = notional / s
        self.last_s[c], self.last_p[c], self.ref[c] = s, p, p
        self.rec["costs"] += _trade_cost(self.q[c], s, p, self.costs)
        self.rec["traded"] += notional

    def resize(self, c, notional: float) -> None:
        """Trade an existing position to ``notional`` (both legs); the liquidation reference is kept."""
        dq = notional / self.s_t[c] - self.q[c]
        self.trades.append((self.t, self.name, c, "resize", abs(dq) * self.s_t[c]))
        self.rec["costs"] += _trade_cost(abs(dq), self.s_t[c], self.p_t[c], self.costs)
        self.rec["traded"] += abs(dq) * self.s_t[c]
        self.q[c] += dq

    def adv_cap(self, c) -> float:
        a = self.adv.at[self.t, c] if c in self.adv.columns else np.nan
        return self.costs.adv_cap * a if np.isfinite(a) else 0.0

    def execute_slots(self, target: set, slots: int) -> None:
        """Phase 3 rules: exit coins not in the target, enter new ones at one slot each, never resize."""
        for c in [c for c in self.q if self._priced(c) and c not in target]:
            self.close(c)
        for c in [c for c in target if c not in self.q and c in self.inv and c not in self.blocked and self._priced(c)]:
            notional = min(self.equity / (1 + self.costs.margin_buffer) / slots, self.adv_cap(c))
            if notional > 0:
                self.open(c, notional)

    def free_capital(self) -> float:
        return self.equity - self.deployed() - sum(self.unhedged[c] * self.last_s[c] for c in self.unhedged)

    def execute_notional(self, target: dict[str, float], min_trade: float = 100.0, borrow: bool = False) -> None:
        """Phase 4 allocator: trade each coin toward its target notional (0 or missing = close; NaN = hold
        as is, so a position the allocator left unchanged is not re-traded because its price moved).

        Sells first, then buys limited by the capital actually on this venue (a planned transfer may
        not have arrived yet; the next day's solve buys the rest). ``borrow=True`` lets buys exceed
        equity (leverage); negative cash then pays ``costs.borrow_rate``.
        """
        for c in [c for c in list(self.q) if self._priced(c)]:
            x = target.get(c, 0.0)
            if x <= 0:
                self.close(c)
            elif x < self.notional(c) - min_trade:
                self.resize(c, x)
        free = float("inf") if borrow else self.free_capital()
        for c, x in sorted(((c, x) for c, x in target.items() if np.isfinite(x)), key=lambda kv: -kv[1]):
            held = self.notional(c) if c in self.q else 0.0
            if x - held < min_trade or not (c in self.inv and c not in self.blocked and self._priced(c)):
                continue
            add = min(x - held, max(free, 0.0) / self.margin(c))
            if c not in self.q:
                add = min(add, self.adv_cap(c))
            if add < min_trade:
                continue
            self.resize(c, held + add) if c in self.q else self.open(c, add)
            free -= add * self.margin(c)

    def finish(self, tbill_t: float) -> dict:
        rec = self.rec
        pnl = rec["funding"] + rec["basis"] + rec["unhedged"] + rec["cash"] - rec["costs"] - rec["liquidation"]
        row = {"ts": self.t, "equity_start": self.equity, **rec, "pnl": pnl, "n_held": len(self.q),
               "liquidations": int(rec["liquidation"] > 0), "tbill": tbill_t}
        self.equity += pnl
        if not np.isfinite(self.equity):
            raise FloatingPointError(f"equity became {self.equity} at {self.t}: {rec}")
        return row


def run(panel: dict, forecast: pd.Series, rule: Rule, slots: int, capital: float, tbill: pd.Series,
        costs: Costs, start: str = "2022-01-01") -> pd.DataFrame:
    """Simulate one venue's book with a Phase 3 rule. ``forecast`` is indexed (ts, coin).

    Each new position gets one slot: equity / (1 + margin buffer) / ``slots`` of notional (capped by
    liquidity). Unused slots stay in cash. Positions are not resized while held.

    Timeline at each window close t:
      1. positions held over (t-1, t] earn funding and basis; idle cash earns the T-bill;
      2. liquidations and forced exits (coin no longer investable) are processed at t;
      3. the order decided at t-1 is executed at t's close;
      4. the rule decides the next target from information at t (executed at t+1).
    """
    book = Book(panel, capital, costs)
    fc_by_t = {t: g.droplevel("ts") for t, g in forecast.groupby(level="ts")} if len(forecast) else {}
    target, rows = None, []
    for t in panel["funding"].loc[start:].index:
        tb = tbill.get(t, 0.0)
        book.begin(t, tb)
        if target is not None:
            book.execute_slots(target, slots)
        rows.append(book.finish(tb))
        target = rule(t, set(book.q), book.inv, fc_by_t.get(t, pd.Series(dtype=float)), tb)
    return pd.DataFrame(rows).set_index("ts")


# A daily allocator sees (t, books, capital in transit) and returns
# ({venue: {coin: target notional}}, {(from, to): amount}).
Allocator = Callable[[pd.Timestamp, dict, list], tuple[dict, dict]]


def run_joint(panels: dict, decide: Allocator, nav: float, tbill: pd.Series, costs: dict[str, Costs],
              margin: Callable[[str], float] | None = None, start: str = "2022-01-01",
              transfer_fee: float = 10.0) -> pd.DataFrame:
    """Both venues as one portfolio: one decision a day at the 00:00 close, executed at the next close.

    Transfers leave the source venue at execution and arrive one day later; in transit they earn
    nothing. ``equity_start`` of the combined ledger includes capital in transit.
    """
    books = {v: Book(panels[v], nav / len(panels), costs[v], margin, name=v) for v in panels}
    snapshots = []  # daily positions: (ts, venue, coin, notional)
    transit: list[tuple[pd.Timestamp, str, float]] = []  # (arrival, destination, amount)
    pending, rows = None, []
    for t in next(iter(panels.values()))["funding"].loc[start:].index:
        tb = tbill.get(t, 0.0)
        for b in books.values():
            b.begin(t, tb)
        for item in [i for i in transit if i[0] <= t]:
            books[item[1]].equity += item[2]
            transit.remove(item)
        if pending is not None:
            targets, transfers = pending
            for v, b in books.items():
                b.execute_notional(targets.get(v, {}))
            for (src, dst), amount in transfers.items():
                amount = min(amount, max(books[src].free_capital(), 0.0))
                if amount > 0:
                    books[src].equity -= amount
                    books[src].rec["costs"] += transfer_fee
                    transit.append((t + pd.Timedelta(days=1), dst, amount))
            pending = None
        in_transit = sum(a for _, _, a in transit)
        parts = [b.finish(tb) for b in books.values()]
        total = sum(p["equity_start"] for p in parts) + in_transit
        row = {k: sum(p[k] for p in parts) for k in parts[0] if k not in ("ts", "tbill")}
        row.update(ts=t, tbill=tb, equity_start=total, in_transit=in_transit,
                   max_venue_share=max(b.equity for b in books.values()) / (total + row["pnl"]))
        rows.append(row)
        if t.hour == 0:
            snapshots += [(t, v, c, b.notional(c)) for v, b in books.items() for c in b.q]
            pending = decide(t, books, transit)
    out = pd.DataFrame(rows).set_index("ts")
    out.attrs["positions"] = pd.DataFrame(snapshots, columns=["ts", "venue", "coin", "notional"])
    out.attrs["trades"] = pd.DataFrame([x for b in books.values() for x in b.trades],
                                       columns=["ts", "venue", "coin", "kind", "notional"])
    return out


def _trade_cost(q: float, s: float, p: float, costs: Costs) -> float:
    """Open or close both legs of a q-coin position."""
    return q * (s * (costs.spot_fee + costs.slippage) + p * (costs.perp_fee + costs.slippage))
