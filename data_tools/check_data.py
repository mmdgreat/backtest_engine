"""Data-quality report for the candles stored in MongoDB (does not need MT5).

Run:  python check_data.py              (M5 by default)
      python check_data.py --tf H1
      python check_data.py --drop-duplicates   (deletes repeated bars, keeps the first)
"""
import argparse

import pandas as pd
from pymongo import MongoClient

import config

TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="M5", choices=list(TF_SECONDS))
    parser.add_argument("--drop-duplicates", action="store_true")
    args = parser.parse_args()

    coll = MongoClient(config.MONGO_URI)[config.MONGO_DB][config.CANDLES_COLLECTION]
    query = {"symbol": config.SYMBOL, "tf": args.tf}
    docs = list(coll.find(query).sort("time", 1))
    if not docs:
        raise SystemExit(f"No {config.SYMBOL} {args.tf} candles found.")

    df = pd.DataFrame(docs)
    df["time"] = pd.to_datetime(df["time"])
    secs = TF_SECONDS[args.tf]

    print(f"== {config.SYMBOL} {args.tf} ==")
    print(f"rows: {len(df):,} | first: {df['time'].iloc[0]} | last: {df['time'].iloc[-1]}")

    dup_mask = df["time"].duplicated(keep="first")
    print(f"duplicate timestamps: {int(dup_mask.sum())}")
    if dup_mask.any() and args.drop_duplicates:
        ids = df.loc[dup_mask, "_id"].tolist()
        res = coll.delete_many({"_id": {"$in": ids}})
        print(f"  deleted {res.deleted_count} duplicate rows; rerun to confirm")
        df = df[~dup_mask]

    prices = df[["open", "high", "low", "close"]]
    bad = df[
        (df["high"] < prices[["open", "close"]].max(axis=1))
        | (df["low"] > prices[["open", "close"]].min(axis=1))
        | (df["high"] < df["low"])
        | (prices <= 0).any(axis=1)
    ]
    print(f"bars with impossible OHLC: {len(bad)}")
    if len(bad):
        print(bad[["time", "open", "high", "low", "close"]].head(10).to_string(index=False))

    if "spread" in df:
        s = df["spread"]
        print(f"spread (points): min {s.min()} | median {s.median()} | max {s.max()} | zero-spread bars {(s == 0).sum()}")

    if secs <= 14400:
        diffs = df["time"].diff().dt.total_seconds()
        low = max(3 * 3600, 6 * secs)
        gaps = df[(diffs > low) & (diffs < 44 * 3600)]  # >44h is a normal weekend
        print(f"unexpected gaps (> {low / 3600:.0f}h, excluding weekends): {len(gaps)}")
        for idx in gaps.index[:15]:
            prev = df["time"].shift(1).loc[idx]
            print(f"  {prev}  ->  {df.loc[idx, 'time']}  ({diffs.loc[idx] / 3600:.1f} h)")
        if len(gaps) > 15:
            print(f"  ... and {len(gaps) - 15} more")
        print("note: a few gaps around holidays (Christmas, New Year) are normal")
    else:
        print("gap check skipped for D1/H4+ timeframes")

    idx_names = [i for i in coll.index_information()]
    print(f"indexes: {idx_names}")
    if "symbol_tf_time_unique" not in idx_names:
        print("  no unique index yet; python sync_candles.py will create one")


if __name__ == "__main__":
    main()
