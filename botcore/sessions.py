"""Broker server clock -> real UTC / London / New York time, and session-window helpers.

The stored candle `time` is the broker SERVER clock labelled as UTC (that is how MT5 returns it).
Server time = New York time + 7h (day rolls at 5pm NY), so converting is exact and DST-safe:
    server -> subtract 7h -> read as New York local time -> convert to UTC / London.
"""
import numpy as np
import pandas as pd

_EPOCH = pd.Timestamp("1970-01-01")


def _seconds(index):
    """Naive DatetimeIndex -> int64 epoch seconds (works for any pandas time resolution)."""
    return ((index - _EPOCH) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")


def _day_number(index):
    return ((index.normalize() - _EPOCH) // pd.Timedelta(days=1)).to_numpy(dtype="int64")


def time_features(server_ts, server_minus_ny_hours=7):
    """server_ts: int64 epoch seconds of the server clock. Returns a dict of numpy arrays."""
    idx = pd.DatetimeIndex(pd.to_datetime(np.asarray(server_ts, dtype="int64"), unit="s"))
    ny_naive = idx - pd.Timedelta(hours=server_minus_ny_hours)
    # Ambiguous / non-existent local times only occur on DST Sundays while the market is closed.
    ny = ny_naive.tz_localize(
        "America/New_York", ambiguous=np.ones(len(idx), dtype=bool), nonexistent="shift_forward"
    )
    utc = ny.tz_convert("UTC")
    ldn = utc.tz_convert("Europe/London")
    utc_naive = utc.tz_localize(None)
    ny_local = ny.tz_localize(None)
    ldn_local = ldn.tz_localize(None)
    return {
        "utc_ts": _seconds(utc_naive),
        "utc_min": (utc_naive.hour * 60 + utc_naive.minute).to_numpy(dtype="int32"),
        "ny_min": (ny_local.hour * 60 + ny_local.minute).to_numpy(dtype="int32"),
        "ldn_min": (ldn_local.hour * 60 + ldn_local.minute).to_numpy(dtype="int32"),
        "utc_date": _day_number(utc_naive),
        "ny_date": _day_number(ny_local),
        "ldn_date": _day_number(ldn_local),
        "dow_ny": ny_local.dayofweek.to_numpy(dtype="int8"),
    }


def window_segments(date, minute, start_min, end_min):
    """Bars whose local minute-of-day lies in [start_min, end_min), grouped per local date.
    The window must sit inside one local day. Returns a list of (date, index_array)."""
    mask = (minute >= start_min) & (minute < end_min)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    d = date[idx]
    cuts = np.flatnonzero(np.diff(d) != 0) + 1
    return [(int(date[g[0]]), g) for g in np.split(idx, cuts)]


def clock_for(m, tz):
    """(minute_of_day_array, date_array) for 'london', 'ny' or 'utc'."""
    if tz == "london":
        return m.ldn_min, m.ldn_date
    if tz == "ny":
        return m.ny_min, m.ny_date
    if tz == "utc":
        return m.utc_min, m.utc_date
    raise ValueError(f"unknown tz {tz}")
