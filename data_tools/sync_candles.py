"""Phase 1: incrementally sync MT5 candles into MongoDB.

Safe to run repeatedly: it resumes from the newest stored bar and upserts, so no duplicates.
Run:  python sync_candles.py                 (default timeframes from config.py)
      python sync_candles.py --tf M1 M5 H1   (several timeframes)
      python sync_candles.py --tf M1 --since 2021-01-04   (first M1 load: about 1.7M bars for 5 years, takes a while)
      python sync_candles.py --since 2022-01-01   (used only for a timeframe with no data yet)
      python sync_candles.py --backfill --since 2021-01-01   (load OLDER history before your oldest stored bar)

Stored `time` is the broker server time labelled as UTC, exactly as MT5 returns it
(this matches the data already in your collection). Do not mix in true-UTC rows.
"""
import argparse
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.errors import OperationFailure

import config
from mt5_common import TF_MAP, TF_SECONDS, connect_mt5

# Days per request, so each call stays well under the terminal's bar limit
CHUNK_DAYS = {"M1": 7, "M5": 30, "M15": 60, "M30": 90, "H1": 180, "H4": 365, "D1": 365}


def ensure_index(coll):
    try:
        coll.create_index(
            [("symbol", ASCENDING), ("tf", ASCENDING), ("time", ASCENDING)],
            unique=True,
            name="symbol_tf_time_unique",
        )
    except OperationFailure as exc:
        raise SystemExit(
            f"Could not create the unique index ({exc}).\n"
            "Duplicates probably exist. Run: python check_data.py --drop-duplicates  then retry."
        )


def server_now(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise SystemExit(f"No tick for {symbol}: {mt5.last_error()}")
    return datetime.fromtimestamp(tick.time, tz=timezone.utc)


def as_utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def sync_timeframe(coll, symbol, tf, since, backfill=False):
    tf_sec = TF_SECONDS[tf]
    last = coll.find_one({"symbol": symbol, "tf": tf}, sort=[("time", -1)])
    first = coll.find_one({"symbol": symbol, "tf": tf}, sort=[("time", 1)])
    if backfill and first:
        # Load the older history: from --since up to just past the oldest bar already stored.
        start = since
        end = as_utc(first["time"]) + timedelta(seconds=tf_sec * 3)
        if start >= end:
            print(f"[{tf}] nothing to backfill: oldest stored bar {first['time']} is already at or before --since")
            return
    else:
        start = as_utc(last["time"]) - timedelta(seconds=tf_sec * 3) if last else since
        end = server_now(symbol)
    newest_complete = end - timedelta(seconds=tf_sec)  # a bar is final only once it has closed

    print(f"[{tf}] from {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M} (server time)")
    cursor, total, n_chunks = start, 0, 0
    step = timedelta(days=CHUNK_DAYS[tf])
    while cursor < end:
        n_chunks += 1
        if n_chunks % 25 == 0:
            print(f"  ... {cursor:%Y-%m-%d} reached, {total:,} bars so far")
        chunk_end = min(cursor + step, end + timedelta(minutes=1))
        rates = mt5.copy_rates_range(symbol, TF_MAP[tf], cursor, chunk_end)
        if rates is None:
            print(f"  warning: no data for {cursor:%Y-%m-%d}..{chunk_end:%Y-%m-%d}: {mt5.last_error()}")
        else:
            ops = []
            for r in rates:
                t = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
                if t > newest_complete:
                    continue
                doc = {
                    "time": t,
                    "symbol": symbol,
                    "tf": tf,
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "tick_volume": int(r["tick_volume"]),
                    "real_volume": int(r["real_volume"]),
                    "spread": int(r["spread"]),
                }
                ops.append(UpdateOne({"symbol": symbol, "tf": tf, "time": t}, {"$set": doc}, upsert=True))
            if ops:
                coll.bulk_write(ops, ordered=False)
                total += len(ops)
        cursor = chunk_end
    print(f"[{tf}] upserted {total} bars")
    oldest = coll.find_one({"symbol": symbol, "tf": tf}, sort=[("time", 1)])
    stored = coll.count_documents({"symbol": symbol, "tf": tf})
    if oldest:
        print(f"[{tf}] now stored: {stored:,} bars, oldest {oldest['time']}")
        if not backfill and as_utc(oldest["time"]) - since > timedelta(days=14):
            print(f"[{tf}] WARNING: the oldest bar is later than --since {since:%Y-%m-%d}. The broker/terminal only holds "
                  f"history from about {oldest['time']:%Y-%m-%d}. If you need more, open a {tf} chart in MT5, set "
                  "Tools > Options > Charts > Max bars in chart = Unlimited, press Home on the chart to download "
                  "history, then run this again.")


def save_specs(db, symbol):
    info = mt5.symbol_info(symbol)._asdict()
    keys = (
        "digits", "point", "trade_contract_size", "volume_min", "volume_max", "volume_step",
        "trade_tick_size", "trade_tick_value", "trade_stops_level", "trade_freeze_level",
        "filling_mode", "swap_long", "swap_short", "spread",
        "currency_base", "currency_profit", "currency_margin",
    )
    doc = {k: info[k] for k in keys if k in info}
    doc.update({"symbol": symbol, "captured_at": datetime.now(timezone.utc)})
    db[config.SPECS_COLLECTION].replace_one({"symbol": symbol}, doc, upsert=True)
    print("saved broker symbol specs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", nargs="+", default=config.DEFAULT_TIMEFRAMES, choices=list(TF_MAP))
    parser.add_argument("--since", default=config.DEFAULT_SINCE, help="YYYY-MM-DD")
    parser.add_argument("--backfill", action="store_true",
                        help="load older history from --since up to the oldest stored bar (instead of newer bars)")
    args = parser.parse_args()
    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    connect_mt5()
    db = MongoClient(config.MONGO_URI)[config.MONGO_DB]
    coll = db[config.CANDLES_COLLECTION]
    ensure_index(coll)
    for tf in args.tf:
        sync_timeframe(coll, config.SYMBOL, tf, since, backfill=args.backfill)
    save_specs(db, config.SYMBOL)
    mt5.shutdown()


if __name__ == "__main__":
    main()
