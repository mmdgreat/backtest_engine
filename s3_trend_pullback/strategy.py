"""S3 Trend Pullback.

Trend (H1, completed bars only): fast EMA above slow EMA and rising = up; below and falling = down.
Entry (M5): in an uptrend, a bar whose low reaches the M5 EMA band (EMA + band_atr x ATR) and CLOSES back above
the EMA on a bullish candle, after price had been extended at least min_ext_atr x ATR above the EMA in the previous
ext_lookback bars. Shorts mirror this. Only inside the New York window, with a spread filter and a cooldown.
Stop = stop_atr x ATR, target = rr x stop (and/or a chandelier trail), time stop and flat before the rollover."""
import numpy as np

from botcore import indicators as ind
from botcore.signals import SignalSet
from botcore.util import exit_ts_at, hhmm, spread_ok

TAGS = ["long", "short"]


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    h1 = m.htf(3600)
    fast = ind.ema(h1.c, int(p["h1_fast"]))
    slow = ind.ema(h1.c, int(p["h1_slow"]))
    prev = ind.shift(fast, int(p["slope_bars"]))
    with np.errstate(invalid="ignore"):
        trend = np.where((fast > slow) & (fast > prev), 1.0, np.where((fast < slow) & (fast < prev), -1.0, 0.0))
    trend[np.isnan(fast) | np.isnan(slow) | np.isnan(prev)] = np.nan
    t = m.align(h1, trend)                     # H1 value as known at the close of each M5 bar

    ema = m.ema(int(p["pull_ema"]))
    atr = m.atr(int(p["atr_len"]))
    band = p["band_atr"] * atr
    lb = int(p["ext_lookback"])
    ext_up = ind.shift(ind.rolling_max(m.h - ema, lb), 1)
    ext_dn = ind.shift(ind.rolling_max(ema - m.l, lb), 1)
    min_ext = p["min_ext_atr"] * atr
    w0, w1 = hhmm(p["window_ny"][0]), hhmm(p["window_ny"][1])
    in_win = (m.ny_min >= w0) & (m.ny_min < w1)
    with np.errstate(invalid="ignore"):
        long_c = (t == 1) & in_win & (m.l <= ema + band) & (m.c > ema) & (m.c > m.o) & (ext_up >= min_ext)
        short_c = (t == -1) & in_win & (m.h >= ema - band) & (m.c < ema) & (m.c < m.o) & (ext_dn >= min_ext)

    flat = hhmm(p["flat_ny"])
    cool = int(p["cooldown_bars"])
    last = -10 ** 9
    for i in np.flatnonzero(long_c | short_c):
        if i - last < cool or not spread_ok(m, i, p["max_spread"]):
            continue
        a = atr[i]
        if a != a:
            continue
        side = 1 if long_c[i] else -1
        risk = p["stop_atr"] * a
        stop = m.c[i] - side * risk
        target = m.c[i] + side * p["rr"] * risk if p["rr"] > 0 else np.nan
        trail = p["trail_atr"] * a if p["trail_atr"] > 0 else np.nan
        if sigs.add(i, side, stop, target, trail=trail, exit_ts=exit_ts_at(m, i, "ny", flat),
                    max_bars=int(p["max_hold_bars"]), tag=0 if side > 0 else 1):
            last = i
    return sigs
