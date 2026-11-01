"""S2 Liquidity Sweep + Reversal (SMC style).

Liquidity pools: the Asian range high/low, the previous trading day's high/low, the London session high/low.
Inside the London / New York kill zones:
  1. SWEEP: price trades beyond a pool by at least sweep_min_atr x ATR, then a bar CLOSES back inside the pool
     within max_return_bars bars. (Closing back inside is what separates a sweep from a breakout.)
  2. STRUCTURE SHIFT: within max_shift_bars bars, a bar closes through the last confirmed M5 swing point on
     the other side (below the last swing low after a high sweep = short; above the last swing high after a
     low sweep = long). If price takes out the sweep extreme first, the setup is cancelled.
  3. Stop sl_buf_atr x ATR beyond the sweep extreme, target rr x the stop distance. Each pool is used once
     per kill zone per day."""
import numpy as np

from botcore.sessions import window_segments
from botcore.signals import SignalSet
from botcore.util import confirmed_swings, exit_ts_at, hhmm

TAGS = ["asia", "prev_day", "london"]


def _local_session_levels(m, date, minute, start_min, end_min, min_bars=20):
    """High/low of a local-clock window, available to every later bar of that local day from end_min on."""
    n = m.n
    hi, lo = np.full(n, np.nan), np.full(n, np.nan)
    for d, idx in window_segments(date, minute, start_min, end_min):
        if len(idx) < min_bars:
            continue
        a, b = np.searchsorted(date, d, "left"), np.searchsorted(date, d, "right")
        seg = np.arange(a, b)
        seg = seg[minute[a:b] >= end_min]
        hi[seg] = m.h[idx].max()
        lo[seg] = m.l[idx].min()
    return hi, lo


def _prev_day_levels(m, min_day_bars):
    n = m.n
    sd = m.sday
    starts = np.concatenate(([0], np.flatnonzero(np.diff(sd)) + 1))
    ends = np.append(starts[1:], n)
    dh = np.maximum.reduceat(m.h, starts)
    dl = np.minimum.reduceat(m.l, starts)
    hi, lo = np.full(n, np.nan), np.full(n, np.nan)
    for k in range(1, len(starts)):
        if ends[k - 1] - starts[k - 1] >= min_day_bars and sd[starts[k]] - sd[starts[k - 1]] <= 4:
            hi[starts[k]:ends[k]] = dh[k - 1]
            lo[starts[k]:ends[k]] = dl[k - 1]
    return hi, lo


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    n = m.n
    h, l, c, o = m.h, m.l, m.c, m.o
    atr = m.atr(int(p["atr_len"]))
    swing_hi, swing_lo = confirmed_swings(h, l, int(p["swing_k"]))
    a_end, l_end = hhmm(p["asia_end_london"]), hhmm(p["london_end"])

    pools = {}
    if "asia" in p["levels"]:
        pools["asia"] = _local_session_levels(m, m.ldn_date, m.ldn_min, 0, a_end)
    if "prev_day" in p["levels"]:
        pools["prev_day"] = _prev_day_levels(m, int(p["min_day_bars"]))
    if "london" in p["levels"]:
        pools["london"] = _local_session_levels(m, m.ldn_date, m.ldn_min, a_end, l_end)

    # kill zones: an id that is unique per (zone, local day); -1 outside
    zone = np.full(n, -1, dtype=np.int64)
    k0, k1 = hhmm(p["kill_london"][0]), hhmm(p["kill_london"][1])
    zone[(m.ldn_min >= k0) & (m.ldn_min < k1)] = m.ldn_date[(m.ldn_min >= k0) & (m.ldn_min < k1)] * 2
    n0, n1 = hhmm(p["kill_ny"][0]), hhmm(p["kill_ny"][1])
    in_ny = (m.ny_min >= n0) & (m.ny_min < n1)
    zone[in_ny] = m.ny_date[in_ny] * 2 + 1

    flat = hhmm(p["flat_ny"])
    max_ret, max_shift = int(p["max_return_bars"]), int(p["max_shift_bars"])
    pending, setups, used = {}, [], set()
    cur_zone = None
    for i in range(n):
        z = zone[i]
        if z != cur_zone:
            pending.clear()
            setups.clear()
            cur_zone = z
        if z < 0:
            continue
        a = atr[i]
        if a != a:
            continue
        min_sweep = p["sweep_min_atr"] * a
        for name, (hi_arr, lo_arr) in pools.items():
            for kind in (1, -1):                       # 1: a high is swept (short setup); -1: a low (long setup)
                lv = hi_arr[i] if kind == 1 else lo_arr[i]
                if lv != lv or (z, name, kind) in used:
                    continue
                key = (name, kind)
                poked = (h[i] > lv + min_sweep) if kind == 1 else (l[i] < lv - min_sweep)
                back_in = (c[i] < lv) if kind == 1 else (c[i] > lv)
                ext_now = h[i] if kind == 1 else l[i]
                if key in pending:
                    pk = pending[key]
                    pk[1] = max(pk[1], ext_now) if kind == 1 else min(pk[1], ext_now)
                    if back_in:
                        if i - pk[0] <= max_ret:
                            setups.append({"side": -kind, "ext": pk[1], "born": i, "key": key,
                                           "trig": swing_lo[i] if kind == 1 else swing_hi[i]})
                            used.add((z, name, kind))
                        del pending[key]
                    elif i - pk[0] >= max_ret:
                        del pending[key]
                elif poked:
                    if back_in:
                        setups.append({"side": -kind, "ext": ext_now, "born": i, "key": key,
                                       "trig": swing_lo[i] if kind == 1 else swing_hi[i]})
                        used.add((z, name, kind))
                    else:
                        pending[key] = [i, ext_now]
        fired = None
        for s in list(setups):
            if i - s["born"] > max_shift:
                setups.remove(s)
                continue
            if s["side"] == -1:
                if h[i] > s["ext"]:
                    setups.remove(s)
                    continue
                if s["trig"] == s["trig"] and c[i] < s["trig"]:
                    fired = s
            else:
                if l[i] < s["ext"]:
                    setups.remove(s)
                    continue
                if s["trig"] == s["trig"] and c[i] > s["trig"]:
                    fired = s
            if fired:
                break
        if fired:
            setups.remove(fired)
            side = fired["side"]
            stop = fired["ext"] + p["sl_buf_atr"] * a * (1 if side < 0 else -1)
            risk = side * (c[i] - stop)
            if risk > 0:
                sigs.add(i, side, stop, c[i] + side * p["rr"] * risk,
                         exit_ts=exit_ts_at(m, i, "ny", flat), max_bars=int(p["max_hold_bars"]),
                         tag=TAGS.index(fired["key"][0]))
    return sigs
