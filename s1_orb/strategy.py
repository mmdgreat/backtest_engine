"""S1 Opening Range Breakout.

For each session open (London, New York): the high/low of the first `range_min` minutes is the opening range.
The FIRST close beyond the range within `entry_window_min` minutes after it is the signal (long above, short
below), provided the range is neither too narrow nor too wide relative to ATR. One attempt per session per day.
Stop = atr_mult x ATR (or the far side of the range), target = rr x stop, time stop and flat before the rollover."""
from botcore.sessions import clock_for, window_segments
from botcore.signals import SignalSet
from botcore.util import exit_ts_at, hhmm

TAGS = ["london", "ny"]


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    atr = m.atr(int(p["atr_len"]))
    h, l, c = m.h, m.l, m.c
    flat = hhmm(p["flat_ny"])
    bar_min = m.tf_sec / 60.0
    for name in p["sessions"]:
        if name not in TAGS:
            raise ValueError(f"unknown session '{name}', use london and/or ny")
        minute, date = clock_for(m, name)
        open_min = hhmm(p["london_open"] if name == "london" else p["ny_open"])
        rng_end = open_min + int(p["range_min"])
        win_end = rng_end + int(p["entry_window_min"])
        need = int(0.8 * p["range_min"] / bar_min)           # tolerate a few missing bars, not a hole
        ranges = {}
        for d, idx in window_segments(date, minute, open_min, rng_end):
            if len(idx) >= need:
                ranges[d] = (h[idx].max(), l[idx].min())
        for d, idx in window_segments(date, minute, rng_end, win_end):
            if d not in ranges:
                continue
            hi, lo = ranges[d]
            for i in idx:
                side = 1 if c[i] > hi else (-1 if c[i] < lo else 0)
                if side == 0:
                    continue
                a = atr[i]
                width = hi - lo
                if a == a and p["min_range_atr"] * a <= width <= p["max_range_atr"] * a:
                    stop = (lo if side > 0 else hi) if p["stop_mode"] == "range" else c[i] - side * p["atr_mult"] * a
                    risk = side * (c[i] - stop)
                    sigs.add(i, side, stop, c[i] + side * p["rr"] * risk,
                             exit_ts=exit_ts_at(m, i, "ny", flat), max_bars=int(p["max_hold_bars"]),
                             tag=TAGS.index(name))
                break                                        # only the first break of the window counts
    return sigs
