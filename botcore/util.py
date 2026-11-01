"""Small helpers the strategy modules share. Everything here is causal (uses only bars <= i)."""
import numpy as np
import pandas as pd

from . import indicators as ind


def hhmm(s):
    """'08:20' -> minutes since midnight."""
    h, mm = str(s).split(":")
    return int(h) * 60 + int(mm)


def exit_ts_at(m, i, tz, minute):
    """Broker-clock timestamp at which a trade signalled on bar i must be closed: the next time the
    'ny' or 'london' wall clock reads `minute` (minutes since midnight), on the same local day.
    The broker clock is New York + 7h, so differences on the local clock carry over exactly."""
    cur = int(m.ny_min[i] if tz == "ny" else m.ldn_min[i])
    return int(m.ts[i]) + (int(minute) - cur) * 60


def ffill(a):
    return pd.Series(a).ffill().to_numpy()


def confirmed_swings(h, l, n):
    """Price of the most recent swing high / swing low that is CONFIRMED at each bar.
    A swing at bar k needs n lower highs (higher lows) on each side, so it is only known from bar k+n."""
    is_sh, is_sl = ind.fractal_swings(h, l, n)
    size = len(h)
    ch = np.full(size, np.nan)
    cl = np.full(size, np.nan)
    ih = np.flatnonzero(is_sh)
    il = np.flatnonzero(is_sl)
    ch[ih + n] = h[ih]
    cl[il + n] = l[il]
    return ffill(ch), ffill(cl)


def htf_bar_is_full(m, htf, k, slack_sec=900):
    """True when the last base bar inside HTF bucket k sits within `slack_sec` of the bucket's end,
    i.e. the bucket was not cut short by a data hole."""
    i = htf.last[k]
    return (htf.end_ts[k] - (int(m.ts[i]) + m.tf_sec)) <= slack_sec


def spread_ok(m, i, max_spread):
    return m.spread[i] <= max_spread
