"""S5 Mean Reversion (Bollinger fade, Asian session).

Inside the Asian window (London clock) and only while the market is quiet and choppy (efficiency ratio below
er_max, ATR not above max_atr_ratio x its one-day average): when the previous bar closed OUTSIDE the previous
bar's Bollinger band and this bar closes back INSIDE it, fade the move (below the lower band = long, above the
upper = short). Target = the Bollinger mid-band at the signal. Stop = beyond the extreme of the last 3 bars plus
stop_buf_atr x ATR. The trade is skipped when the reward to the mid-band is smaller than min_rr x the risk.
Always flat when the window ends."""
import numpy as np

from botcore import indicators as ind
from botcore.signals import SignalSet
from botcore.util import exit_ts_at, hhmm, spread_ok

TAGS = ["long", "short"]


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    mid, up, lo = ind.bollinger(m.c, int(p["bb_len"]), p["bb_k"])
    atr = m.atr(int(p["atr_len"]))
    er = ind.efficiency_ratio(m.c, int(p["er_len"]))
    atr_avg = ind.sma(atr, int(p["atr_avg_len"]))
    s0, s1 = hhmm(p["window_london"][0]), hhmm(p["window_london"][1])
    in_win = (m.ldn_min >= s0) & (m.ldn_min < s1)
    prev_c = ind.shift(m.c, 1)
    prev_up, prev_lo = ind.shift(up, 1), ind.shift(lo, 1)
    low3, high3 = ind.rolling_min(m.l, 3), ind.rolling_max(m.h, 3)
    with np.errstate(invalid="ignore"):
        quiet = (er < p["er_max"]) & (atr <= p["max_atr_ratio"] * atr_avg)
        long_c = in_win & quiet & (prev_c < prev_lo) & (m.c > lo)
        short_c = in_win & quiet & (prev_c > prev_up) & (m.c < up)

    for i in np.flatnonzero(long_c | short_c):
        if not spread_ok(m, i, p["max_spread"]):
            continue
        side = 1 if long_c[i] else -1
        a = atr[i]
        if a != a or mid[i] != mid[i]:
            continue
        stop = (low3[i] - p["stop_buf_atr"] * a) if side > 0 else (high3[i] + p["stop_buf_atr"] * a)
        risk = side * (m.c[i] - stop)
        reward = side * (mid[i] - m.c[i])
        if risk <= 0 or reward < p["min_rr"] * risk:
            continue
        sigs.add(i, side, stop, mid[i], exit_ts=exit_ts_at(m, i, "london", s1),
                 max_bars=int(p["max_hold_bars"]), tag=0 if side > 0 else 1)
    return sigs
