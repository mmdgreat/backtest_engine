"""Candle loading (MongoDB or CSV) and the Market object every strategy works on."""
import types

import numpy as np
import pandas as pd

from . import indicators as ind
from . import settings
from .sessions import time_features

REQUIRED = ["time", "open", "high", "low", "close"]


def load_candles_mongo(symbol=None, tf=None, uri=None, db=None, coll=None, start=None, end=None):
    from pymongo import MongoClient
    symbol = symbol or settings.SYMBOL
    tf = tf or settings.TIMEFRAME
    client = MongoClient(uri or settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    c = client[db or settings.MONGO_DB][coll or settings.CANDLES_COLLECTION]
    q = {"symbol": symbol, "tf": tf}
    if start or end:
        q["time"] = {}
        if start:
            q["time"]["$gte"] = pd.Timestamp(start).to_pydatetime()
        if end:
            q["time"]["$lt"] = pd.Timestamp(end).to_pydatetime()
    proj = {"_id": 0, "time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "tick_volume": 1, "spread": 1}
    df = pd.DataFrame(list(c.find(q, proj).sort("time", 1)))
    if df.empty:
        raise SystemExit(f"No {symbol} {tf} candles found in {settings.MONGO_DB}.{settings.CANDLES_COLLECTION}")
    return df


def load_candles_csv(path):
    return pd.read_csv(path)


def clean(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"candles missing columns: {missing}")
    df = df.copy()
    t = pd.to_datetime(df["time"])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    df["time"] = t
    for col in ("tick_volume", "spread"):
        if col not in df.columns:
            df[col] = 0
    df = df.dropna(subset=REQUIRED).sort_values("time")
    df = df.drop_duplicates(subset="time", keep="first")
    ok = (df[["open", "high", "low", "close"]] > 0).all(axis=1) & (df["high"] >= df["low"])
    df = df[ok]
    return df.reset_index(drop=True)


class HTF:
    """Higher-timeframe bars built from the base bars, aligned to the broker clock like MT5 does
    (H1 on the hour, H4 at 00/04/08.., D1 at server midnight)."""

    def __init__(self, m, sec):
        bucket = m.ts // sec
        starts = np.concatenate(([0], np.flatnonzero(np.diff(bucket)) + 1))
        self.sec = sec
        self.first = starts
        self.last = np.append(starts[1:], m.n) - 1
        self.start_ts = bucket[starts] * sec
        self.end_ts = self.start_ts + sec
        self.o = m.o[starts]
        self.c = m.c[self.last]
        self.h = np.maximum.reduceat(m.h, starts)
        self.l = np.minimum.reduceat(m.l, starts)
        self.n = len(starts)
        # A bucket counts as complete once a later bucket exists. The final bucket of the data
        # is dropped so a signal can never be built from a half-formed bar.
        self.complete = np.ones(self.n, dtype=bool)
        self.complete[-1] = False

    def signal_index(self):
        """Base-bar index at whose close each HTF bar is known (last base bar inside the bucket)."""
        return self.last


class Market:
    def __init__(self, df, point=None, server_minus_ny_hours=None, spread_add=0.0):
        """spread_add: price units added to every bar's stored spread, for when the candle field understates
        the spread really paid (measure it with data_tools/check_spread.py)."""
        point = settings.POINT if point is None else point
        sm = settings.SERVER_MINUS_NY_HOURS if server_minus_ny_hours is None else server_minus_ny_hours
        df = clean(df)
        self.n = len(df)
        if self.n < 100:
            raise ValueError("not enough candles")
        t = pd.DatetimeIndex(df["time"])
        self.ts = ((t - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")
        self.o = df["open"].to_numpy(dtype=float)
        self.h = df["high"].to_numpy(dtype=float)
        self.l = df["low"].to_numpy(dtype=float)
        self.c = df["close"].to_numpy(dtype=float)
        self.spread_add = float(spread_add)
        self.spread = df["spread"].to_numpy(dtype=float) * point + self.spread_add     # price units
        self.vol = df["tick_volume"].to_numpy(dtype=float)
        self.sday = self.ts // 86400                                    # trading day (rolls 5pm NY)
        d = np.diff(self.ts)
        self.tf_sec = int(np.median(d)) if len(d) else 300
        for k, v in time_features(self.ts, sm).items():
            setattr(self, k, v)
        self._cache = {}
        self._py = None

    # -- cached indicators ------------------------------------------------------------------
    def atr(self, n=14):
        key = ("atr", n)
        if key not in self._cache:
            self._cache[key] = ind.atr(self.h, self.l, self.c, n)
        return self._cache[key]

    def ema(self, n):
        key = ("ema", n)
        if key not in self._cache:
            self._cache[key] = ind.ema(self.c, n)
        return self._cache[key]

    def htf(self, sec):
        key = ("htf", sec)
        if key not in self._cache:
            self._cache[key] = HTF(self, sec)
        return self._cache[key]

    def align(self, htf, values):
        """Value of an HTF array as known at the close of each base bar (no look-ahead)."""
        pos = np.searchsorted(htf.end_ts, self.ts + self.tf_sec, side="right") - 1
        out = np.full(self.n, np.nan)
        ok = pos >= 0
        out[ok] = np.asarray(values, dtype=float)[pos[ok]]
        return out

    # -- plain-python views for the simulator's inner loop ------------------------------------
    @property
    def py(self):
        if self._py is None:
            self._py = types.SimpleNamespace(
                ts=self.ts.tolist(), o=self.o.tolist(), h=self.h.tolist(), l=self.l.tolist(),
                c=self.c.tolist(), spread=self.spread.tolist(), sday=self.sday.tolist(),
            )
        return self._py

    def when(self, i):
        return str(pd.Timestamp(int(self.ts[i]), unit="s"))

    def describe(self):
        return (f"{self.n:,} bars | {self.when(0)} -> {self.when(self.n - 1)} (broker time) | "
                f"base {self.tf_sec // 60} min" + (f" | spread +{self.spread_add:g}" if self.spread_add else ""))


def load_market(source="mongo", csv=None, tf=None, start=None, end=None, spread_add=0.0):
    if source == "csv":
        if not csv:
            raise SystemExit("--source csv needs --csv PATH")
        df = load_candles_csv(csv)
        df["time"] = pd.to_datetime(df["time"])
        if start:
            df = df[df["time"] >= pd.Timestamp(start)]
        if end:
            df = df[df["time"] < pd.Timestamp(end)]
    else:
        df = load_candles_mongo(tf=tf, start=start, end=end)
    return Market(df, spread_add=spread_add)
