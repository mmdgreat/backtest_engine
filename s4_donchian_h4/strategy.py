"""S4 Donchian / H4 Breakout.

On each COMPLETED H4 bar: if it closes above the highest high of the previous `channel` H4 bars it is a long
signal; below the lowest low, a short. Optional filter: only trade in the direction of the H4 EMA (price above
it for longs). The stop starts at atr_mult x H4 ATR from entry and trails behind the best price by the same
distance (chandelier exit). There is no fixed target: winners run until the trail is hit or the time stop."""
import numpy as np

from botcore import indicators as ind
from botcore.signals import SignalSet
from botcore.util import htf_bar_is_full, spread_ok

TAGS = ["long", "short"]


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    h4 = m.htf(4 * 3600)
    n_ch = int(p["channel"])
    upper = ind.shift(ind.rolling_max(h4.h, n_ch), 1)     # excludes the signal bar itself
    lower = ind.shift(ind.rolling_min(h4.l, n_ch), 1)
    atr4 = ind.atr(h4.h, h4.l, h4.c, int(p["atr_len"]))
    ef = int(p["ema_filter"])
    emaf = ind.ema(h4.c, ef) if ef > 0 else None
    max_bars = int(float(p["max_hold_days"]) * 86400 / m.tf_sec)

    for k in range(h4.n):
        if not h4.complete[k] or not htf_bar_is_full(m, h4, k):
            continue
        i = int(h4.last[k])
        if i >= m.n - 1:
            continue
        a = atr4[k]
        c = h4.c[k]
        if a != a:
            continue
        side = 0
        if p["allow_long"] and c > upper[k] and (emaf is None or c > emaf[k]):
            side = 1
        elif p["allow_short"] and c < lower[k] and (emaf is None or c < emaf[k]):
            side = -1
        if side == 0 or not spread_ok(m, i, p["max_spread"]):
            continue
        dist = p["atr_mult"] * a
        sigs.add(i, side, c - side * dist, np.nan, trail=dist, max_bars=max_bars, tag=0 if side > 0 else 1)
    return sigs
