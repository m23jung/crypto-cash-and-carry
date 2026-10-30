"""Extension B: stock and commodity perps as synthetic financing. Spec: docs/plan.md, "Extension B spec".

Run after research/build_extensions.py tradfi:  python research/extension_b_tradfi.py
Writes reports/extension_b/report.md and reports/figures/6_tradfi_breakeven.png. Descriptive only.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from funding.panels import prices_8h, to_8h  # noqa: E402
from funding.sources import _get, coin, fred, yahoo_daily  # noqa: E402
from funding.store import Store  # noqa: E402

OUT = Path("reports/extension_b/report.md")
FIG = Path("reports/figures/6_tradfi_breakeven.png")
MIN_DAYS = 60  # perps with less funding history are left out
MAX_TRACKING_GAP = 0.05  # median |perp / underlying - 1| above this: not the same instrument (e.g. CAT)
MAX_ABS_BASIS = 0.20  # windows beyond this are splits (Yahoo back-adjusts, perps don't) or broken pairs
COMMODITY_TICKERS = {"XAU": "GC=F", "XAG": "SI=F", "XPT": "PL=F", "XPD": "PA=F", "CL": "CL=F", "BZ": "BZ=F",
                     "NATGAS": "NG=F", "COPPER": "HG=F"}
YAHOO_FIX = {"BRKB": "BRK-B"}
TYPE_LABEL = {"EQUITY": "single stock", "ETF": "ETF", "FUTURE": "commodity"}


def tradfi_perps() -> pd.DataFrame:
    """Binance TradFi perps with their underlying type (from Binance) and Yahoo ticker where one exists."""
    info = _get("https://fapi.binance.com/fapi/v1/exchangeInfo")["symbols"]
    rows = []
    for x in info:
        if x["contractType"] != "TRADIFI_PERPETUAL" and "TradFi" not in x.get("underlyingSubType", []):
            continue
        if not x["symbol"].endswith("USDT"):
            continue
        c, kind = coin(x["symbol"]), x.get("underlyingType")
        ticker = {"COMMODITY": COMMODITY_TICKERS.get(c), "EQUITY": YAHOO_FIX.get(c, c)}.get(kind)
        rows.append({"coin": c, "binance_type": kind, "ticker": ticker})
    return pd.DataFrame(rows).drop_duplicates("coin").set_index("coin")


def main():
    store = Store()
    perps = tradfi_perps()
    raw = store.read("funding")
    raw = raw[raw["venue"].isin(["binance", "bybit"]) & raw["coin"].isin(perps.index)]
    # A coin's funding counts only from its Binance TradFi listing: earlier Bybit history under the same
    # name is a different (crypto) instrument, e.g. the GME meme coin.
    listed = raw[raw["venue"] == "binance"].groupby("coin")["ts"].min()
    raw = raw[raw["ts"] >= raw["coin"].map(listed)]
    funding = to_8h(raw)
    perp_px = prices_8h(store.read("perp8h"))
    sofr = (fred("SOFR") / 100).tz_localize("UTC")

    # Underlyings, instrument types and the same-instrument check.
    under, kinds = {}, {}
    for c, t in perps["ticker"].dropna().items():
        try:
            under[c], kinds[c] = yahoo_daily(t)
        except Exception as e:  # noqa: BLE001  a ticker Yahoo doesn't know: reported, not fatal
            print("no Yahoo data for", c, t, e)
    perps["asset_type"] = [TYPE_LABEL.get(kinds.get(c, ""), "other (no US underlying)") for c in perps.index]

    rows, basis_obs = [], []
    for (venue, c), f in funding.items():
        f = f.dropna()
        if (f.index[-1] - f.index[0]).days < MIN_DAYS:
            continue
        days = (f.index[-1] - f.index[0]).days
        fund_ann = f.mean() * 3 * 365
        rate = sofr.reindex(sofr.index.union(f.index)).ffill().reindex(f.index).mean()
        row = {"venue": venue, "coin": c, "asset_type": perps.at[c, "asset_type"], "days": days,
               "funding % a year": fund_ann * 100, "SOFR %": rate * 100}
        # Basis vs underlying: perp close at 00:00 UTC (after the US close) vs that day's underlying close.
        px = perp_px.get((venue, c))
        if c in under and px is not None:
            p0 = px.dropna()
            p0 = p0[p0.index.hour == 0]
            u = under[c].tz_localize("UTC")
            pair = pd.DataFrame({"perp": p0.set_axis(p0.index.normalize() - pd.Timedelta(days=1)),
                                 "under": u}).dropna()
            b = pair["perp"] / pair["under"] - 1
            b = b[b.abs() <= MAX_ABS_BASIS]
            if len(b) >= 20 and b.abs().median() <= MAX_TRACKING_GAP:
                years = (b.index - b.index[0]).days / 365
                drift = np.polyfit(years, b.to_numpy(), 1)[0]  # basis change per year (regression slope)
                row.update({"median basis bp": b.median() * 1e4, "basis drift % a year": drift * 100})
                basis_obs.append(b.rename((venue, c)))
            elif len(b) >= 20:
                row["asset_type"] = "excluded: does not track underlying"
        row["break-even spread s* %"] = row["funding % a year"] - row["SOFR %"] - row.get("basis drift % a year", 0.0)
        # Weekend vs weekday (UTC day of the window's end).
        weekend = f.index.dayofweek >= 5
        row["weekend funding % a year"] = f[weekend].mean() * 3 * 365 * 100
        row["weekday funding % a year"] = f[~weekend].mean() * 3 * 365 * 100
        if row["asset_type"] == "other (no US underlying)" and venue != "binance":
            continue  # no underlying to verify the instrument: Binance's own TradFi tag only
        if row["asset_type"] in ("single stock", "ETF", "commodity") and "median basis bp" not in row:
            continue  # core types must pass the same-instrument check
        row["share of prints exactly 0"] = (f == 0).mean()
        rows.append(row)
    t = pd.DataFrame(rows)

    out = ["# Extension B: stock and commodity perps as synthetic financing\n\n"
           f"Binance and Bybit TradFi perps with at least {MIN_DAYS} days of funding; underlying closes from "
           "Yahoo Finance; SOFR from FRED. Descriptive only. Spec: [docs/plan.md](../../docs/plan.md).\n\n"
           "**Early data:** most TradFi perps listed around mid-2026, so histories are a few months long and "
           "annualised figures are early estimates.\n\n"
           "**Break-even spread s\\*** = annualised funding − SOFR − annualised change in the perp's basis to its "
           "underlying. A long holder prefers the perp to stock financed at SOFR + s whenever s > s\\*; an "
           "arbitrageur (long stock, short perp) earns carry whenever their financing spread is below s\\*.\n"]

    def section(title, df, note="", fmt=".2f"):
        out.append(f"\n## {title}\n\n" + (f"{note}\n\n" if note else "") + df.to_markdown(floatfmt=fmt) + "\n")

    counts = t.groupby(["asset_type", "venue"]).size().unstack(fill_value=0)
    section("0. Coverage", counts, "Perps per asset type and venue.", fmt=".0f")

    core = t[t["asset_type"].isin(["single stock", "ETF", "commodity"])]
    by_type = core.groupby("asset_type").agg(
        perps=("coin", "size"), median_days=("days", "median"),
        **{"funding % a year (median)": ("funding % a year", "median"),
           "SOFR %": ("SOFR %", "median"),
           "s* median %": ("break-even spread s* %", "median"),
           "s* 25th pct %": ("break-even spread s* %", lambda s: s.quantile(0.25)),
           "s* 75th pct %": ("break-even spread s* %", lambda s: s.quantile(0.75)),
           "share with s* < 0": ("break-even spread s* %", lambda s: (s < 0).mean()),
           "median basis bp": ("median basis bp", "median"),
           "share of funding prints = 0": ("share of prints exactly 0", "median")})
    section("1. Implied financing and break-even spread by asset type", by_type,
            "Per perp over its full history, then summarised across perps. s* < 0 means the perp is *cheaper* "
            "than SOFR-financed cash exposure even before any spread.")
    other = t[t["asset_type"] == "other (no US underlying)"]
    if len(other):
        section("1b. Perps without a US underlying (Asian equities, pre-IPO, FX): implied financing only",
                other.groupby("asset_type")[["funding % a year", "SOFR %"]].median()
                .assign(**{"funding − SOFR %": lambda d: d["funding % a year"] - d["SOFR %"]}))
    top = core.sort_values("break-even spread s* %", ascending=False)
    cols = ["venue", "coin", "asset_type", "days", "funding % a year", "break-even spread s* %", "median basis bp"]
    section("2. Highest and lowest break-even spreads", pd.concat([top.head(8), top.tail(5)])[cols].set_index("coin"))

    # Over time: monthly median s* across perps (funding − SOFR; basis drift is a full-history adjustment).
    monthly = []
    verified = set(zip(core["venue"], core["coin"], strict=True))
    for (venue, c), f in funding.items():
        typ = perps.at[c, "asset_type"] if c in perps.index else None
        if (venue, c) not in verified:
            continue
        m = f.dropna().groupby(f.dropna().index.tz_localize(None).to_period("M")).mean() * 3 * 365 * 100
        monthly.append(m.rename((venue, c, typ)))
    mon = pd.concat(monthly, axis=1).sort_index()
    s_m = sofr.groupby(sofr.index.tz_localize(None).to_period("M")).mean() * 100
    excess = mon.sub(s_m.reindex(mon.index), axis=0)
    by_month = excess.T.groupby(level=2).median().T.round(2)
    by_month["perps"] = mon.notna().sum(axis=1)
    section("3. Funding minus SOFR over time (monthly median across perps, % a year)", by_month.tail(18))

    wk = core.dropna(subset=["weekend funding % a year", "weekday funding % a year"])
    diff = wk["weekend funding % a year"] - wk["weekday funding % a year"]
    test = stats.wilcoxon(diff) if len(diff) >= 10 else None
    weekend_tbl = wk.assign(diff=diff).groupby("asset_type")[["weekday funding % a year", "weekend funding % a year",
                                                              "diff"]].median()
    section("4. Weekend vs weekday funding (median across perps, % a year)", weekend_tbl,
            f"Paired across all perps: median weekend − weekday {diff.median():+.2f} points"
            + (f"; Wilcoxon signed-rank p = {test.pvalue:.3f}." if test else "."))

    both = sorted({c for v, c in verified if v == "binance"} & {c for v, c in verified if v == "bybit"})
    gaps = (funding["bybit"][both] - funding["binance"][both]).loc["2025":]
    majors = "venue in ['binance', 'bybit'] and coin in ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']"
    crypto = to_8h(store.read("funding").query(majors))
    cgap = (crypto["bybit"] - crypto["binance"]).loc[gaps.dropna(how="all").index.min():]

    def integration(g, a, b):
        st = g.stack().dropna()
        df = pd.DataFrame({"y": g.stack(), "x": g.shift(1).stack()}).dropna()
        phi = np.polyfit(df["x"], df["y"], 1)[0]
        corr = pd.concat([a.stack(), b.stack()], axis=1).dropna().corr().iloc[0, 1]
        return {"pairs": g.shape[1], "median |gap| bp/8h": st.abs().median() * 1e4,
                "90th pct |gap| bp/8h": st.abs().quantile(0.9) * 1e4, "venue correlation": corr,
                "gap half-life (hours)": np.log(0.5) / np.log(phi) * 8 if 0 < phi < 1 else np.nan}

    bn, bb = funding["binance"][both].loc["2025":], funding["bybit"][both].loc["2025":]
    integ = pd.DataFrame({
        "TradFi perps": integration(gaps, bn, bb),
        "crypto majors, same period": integration(cgap, crypto["binance"].loc[cgap.index],
                                                  crypto["bybit"].loc[cgap.index]),
    }).T
    section("5. Integration across venues: Binance vs Bybit funding gaps", integ)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out))
    print("".join(out))

    # Figure: distribution of s* by asset type, and monthly median funding − SOFR.
    colors = {"single stock": "#2a78d6", "ETF": "#eb6834", "commodity": "#1baf7a"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), width_ratios=[1, 1.6])
    for i, (typ, g) in enumerate(core.groupby("asset_type")):
        y = g["break-even spread s* %"].clip(-30, 60)
        a1.scatter(np.full(len(y), i) + np.random.default_rng(0).uniform(-0.18, 0.18, len(y)), y, s=14,
                   color=colors.get(typ, "#898781"), alpha=0.7, edgecolor="none")
        a1.plot([i - 0.28, i + 0.28], [y.median()] * 2, color="#0b0b0b", lw=2)
        a1.text(i + 0.3, y.median(), f"{y.median():.1f}%", va="center", fontsize=9)
    types = list(core.groupby("asset_type").groups)
    a1.set_xticks(range(len(types)), [f"{t}\n(n={int((core['asset_type'] == t).sum())})" for t in types])
    a1.axhline(0, color="#c3c2b7", lw=1)
    a1.set_ylabel("break-even spread over SOFR, % a year")
    a1.set_title("Break-even spread s* per perp (clipped at −30/60)", loc="left", fontsize=11, fontweight="bold")
    for typ in by_month.columns.drop("perps"):
        a2.plot(by_month.index.to_timestamp(), by_month[typ], color=colors.get(typ, "#898781"), lw=1.8, label=typ)
    a2.axhline(0, color="#c3c2b7", lw=1)
    a2.set_title("Funding minus SOFR, monthly median across perps (% a year)", loc="left", fontsize=11,
                 fontweight="bold")
    a2.legend(frameon=False)
    a2.tick_params(axis="x", labelrotation=45)
    a2.text(0.01, 0.02, "early months cover few perps (1-25); from 2026-07, 248-284", transform=a2.transAxes,
            fontsize=8, color="#898781")
    for ax in (a1, a2):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(color="#e1e0d9", lw=0.6)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=160, bbox_inches="tight", facecolor="#fcfcfb")
    print("wrote", FIG)


if __name__ == "__main__":
    main()
