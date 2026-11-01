"""Check the stored M1 candles: quality, coverage by year, and agreement with the stored M5 candles.

Run:  python check_m1_vs_m5.py            (needs MongoDB only, not MT5)

What it does
  1. M1 quality: row count, date range, duplicate timestamps, impossible OHLC, zero-spread share.
  2. Coverage by year: how many M5 bars have all 5 of their M1 bars stored (history holes show up here).
  3. Agreement: builds M5 bars out of the M1 bars (open = first, high = max, low = min, close = last) and compares
     them with the M5 bars you already trust. They should match almost exactly. If they do not, the M1 data (or its
     time labels) is wrong and any scalping test on it would be unreliable.
"""
import numpy as np
import pandas as pd

TOL = 0.0051          # price tolerance (one 0.01 tick plus rounding)
OK_MISMATCH = 0.01    # share of compared M5 bars allowed to disagree
OK_COVERAGE = 0.95    # share of M5 bars that must have all five M1 bars


def aggregate_m1_to_m5(m1):
    """m1: DataFrame with time, open, high, low, close, spread. Returns M5 bars built from complete groups of 5."""
    d = m1.sort_values("time").copy()
    d["b"] = d["time"].dt.floor("5min")
    g = d.groupby("b", sort=True)
    out = pd.DataFrame({
        "n": g["open"].size(),
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
    })
    return out


def compare(m1, m5):
    """Pure function. Returns a dict of findings."""
    r = {"m1_rows": len(m1), "m5_rows": len(m5)}
    r["m1_dupes"] = int(m1["time"].duplicated().sum())
    bad = (m1["high"] < m1[["open", "close", "low"]].max(axis=1) - 1e-9) | \
          (m1["low"] > m1[["open", "close", "high"]].min(axis=1) + 1e-9)
    r["m1_impossible"] = int(bad.sum())
    r["m1_zero_spread_pct"] = float(100.0 * (m1["spread"] == 0).mean()) if len(m1) else 0.0
    agg = aggregate_m1_to_m5(m1.drop_duplicates("time"))
    m5i = m5.drop_duplicates("time").set_index("time")
    full = agg[agg["n"] == 5]
    j = full.merge(m5i[["open", "high", "low", "close"]], left_index=True, right_index=True, how="inner",
                   suffixes=("", "_m5"))
    r["compared"] = len(j)
    if len(j):
        diff = np.zeros(len(j), dtype=bool)
        for c in ("open", "high", "low", "close"):
            diff |= (j[c] - j[c + "_m5"]).abs().to_numpy() > TOL
        r["mismatch"] = int(diff.sum())
        r["mismatch_share"] = float(diff.mean())
        r["mismatch_times"] = [str(t) for t in j.index[diff][:5]]
    else:
        r["mismatch"], r["mismatch_share"], r["mismatch_times"] = 0, 0.0, []
    # coverage by year: of the M5 bars that exist, how many have all five M1 bars
    cov = pd.Series(m5i.index.isin(full.index), index=m5i.index)
    r["coverage_by_year"] = {int(y): (int(g.sum()), int(len(g))) for y, g in cov.groupby(cov.index.year)}
    tot = len(cov)
    r["coverage"] = float(cov.sum() / tot) if tot else 0.0
    # M1 bars sitting outside any M5 bar (M1 history reaching further back than M5)
    r["m1_outside_m5"] = int((~agg.index.isin(m5i.index)).sum())
    return r


def verdict(r):
    if r["m1_rows"] == 0:
        return "UNKNOWN", "no M1 candles stored: run sync_candles.py --tf M1 --since 2021-01-04"
    problems = []
    if r["m1_dupes"]:
        problems.append(f"{r['m1_dupes']} duplicate M1 timestamps")
    if r["m1_impossible"]:
        problems.append(f"{r['m1_impossible']} M1 bars with impossible high/low")
    if r["compared"] < 1000:
        problems.append(f"only {r['compared']} M5 bars could be compared with M1 (too few to judge)")
    elif r["mismatch_share"] > OK_MISMATCH:
        problems.append(f"{100 * r['mismatch_share']:.2f}% of M5 bars built from M1 disagree with stored M5 "
                        f"(first at {r['mismatch_times'][:3]}): the M1 time labels or prices may be wrong")
    if r["compared"] >= 1000 and r["coverage"] < OK_COVERAGE:
        problems.append(f"only {100 * r['coverage']:.1f}% of M5 bars have all five M1 bars: M1 history has holes "
                        "or starts later than M5")
    if problems:
        return "CHECK", "; ".join(problems)
    return "OK", (f"M1 agrees with M5 on {100 * (1 - r['mismatch_share']):.2f}% of {r['compared']:,} compared bars "
                  f"and covers {100 * r['coverage']:.1f}% of the M5 history.")


def load(coll, symbol, tf):
    cur = coll.find({"symbol": symbol, "tf": tf},
                    {"_id": 0, "time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "spread": 1}).sort("time", 1)
    df = pd.DataFrame(list(cur))
    if len(df):
        df["time"] = pd.to_datetime(df["time"])
    return df


def main():
    from pymongo import MongoClient
    import config
    coll = MongoClient(config.MONGO_URI)[config.MONGO_DB][config.CANDLES_COLLECTION]
    print("Loading M1 ... (a few million rows can take a minute or two)")
    m1 = load(coll, config.SYMBOL, "M1")
    m5 = load(coll, config.SYMBOL, "M5")
    if m1.empty:
        print(f"UNKNOWN: {verdict({'m1_rows': 0})[1]}")
        return
    r = compare(m1, m5)
    print(f"== {config.SYMBOL} M1 ==")
    print(f"rows: {r['m1_rows']:,} | first: {m1['time'].iloc[0]} | last: {m1['time'].iloc[-1]}")
    print(f"duplicate timestamps: {r['m1_dupes']} | impossible OHLC: {r['m1_impossible']} | "
          f"zero-spread bars: {r['m1_zero_spread_pct']:.2f}%")
    sp = m1["spread"]
    print(f"spread (points): min {int(sp.min())} | median {int(sp.median())} | 95th pct {int(sp.quantile(0.95))} | max {int(sp.max())}")
    print(f"M1 bars outside the stored M5 range: {r['m1_outside_m5']:,}")
    print("\nCoverage by year (M5 bars that have all five M1 bars):")
    for y, (a, b) in r["coverage_by_year"].items():
        print(f"  {y}: {a:,} of {b:,}  ({100 * a / b:.1f}%)")
    print(f"\nAgreement: {r['compared']:,} M5 bars compared, {r['mismatch']:,} differ "
          f"({100 * r['mismatch_share']:.3f}%)")
    status, msg = verdict(r)
    print(f"\n{status}: {msg}")


if __name__ == "__main__":
    main()
