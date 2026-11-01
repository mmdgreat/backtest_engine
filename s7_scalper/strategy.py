"""S7 Scalper (M1).

Windows: only the first hours after the London and New York opens (New York clock), when gold moves most.
M5 trend (completed M5 bars only): fast EMA above slow and rising = up; below and falling = down.

Breakout mode: a M1 bar whose body is at least body_atr x ATR, that closes in the outer 30% of its range and beyond
the previous range_bars bars' high (low), taken only with the M5 trend (unless trend_filter is off).
Pullback mode: inside an M5 trend, price had been extended from the M1 EMA, then a bar reaches the EMA band and
closes back on the trend side on a candle in the trend direction.

Stop = max(stop_atr x ATR, min_stop dollars). Target = rr x stop. Time stop after max_hold_bars minutes.
Cost gate: (spread + cost_allow) / stop must be <= max_cost_frac, so trades where costs would eat too much of the
risked amount are never taken. Signals are known at the close of a bar; the engine enters at the next bar's open."""
import numpy as np

from botcore import indicators as ind
from botcore.signals import SignalSet
from botcore.util import hhmm, spread_ok

TAGS = ["breakout long", "breakout short", "pullback long", "pullback short"]


def _in_windows(m, windows):
    ok = np.zeros(m.n, dtype=bool)
    for a, b in windows:
        ok |= (m.ny_min >= hhmm(a)) & (m.ny_min < hhmm(b))
    return ok


def build_signals(m, p):
    mode = p["mode"]
    if mode not in ("breakout", "pullback", "both"):
        raise SystemExit(f"mode must be breakout, pullback or both, got {mode}")
    if m.tf_sec != 60:
        raise SystemExit(
            f"S7 needs M1 candles but the loaded data is {m.tf_sec // 60}-minute ({m.n:,} bars). Either the M1 candles "
            "are not in MongoDB (DEPLOY_GUIDE Appendix D) or your botcore/ folder is from an older zip: extract the "
            "newest xauusd-bots.zip over the WHOLE project folder with Expand-Archive -Force, not just s7_scalper.")
    sigs = SignalSet(m, tags=TAGS)
    atr = m.atr(int(p["atr_len"]))
    in_win = _in_windows(m, p["windows_ny"])

    m5 = m.htf(300)
    fast = ind.ema(m5.c, int(p["m5_fast"]))
    slow = ind.ema(m5.c, int(p["m5_slow"]))
    prev = ind.shift(fast, int(p["m5_slope_bars"]))
    with np.errstate(invalid="ignore"):
        trend5 = np.where((fast > slow) & (fast > prev), 1.0, np.where((fast < slow) & (fast < prev), -1.0, 0.0))
    trend5[np.isnan(fast) | np.isnan(slow) | np.isnan(prev)] = np.nan
    t = m.align(m5, trend5)                  # M5 trend as known at the close of each M1 bar

    side = np.zeros(m.n, dtype=np.int8)
    tag = np.zeros(m.n, dtype=np.int16)
    rng_bar = m.h - m.l
    body = m.c - m.o

    with np.errstate(invalid="ignore"):
        if mode in ("breakout", "both"):
            L = int(p["range_bars"])
            hi = ind.shift(ind.rolling_max(m.h, L), 1)
            lo = ind.shift(ind.rolling_min(m.l, L), 1)
            strong = p["body_atr"] * atr
            top = m.c - m.l >= p["close_pos"] * rng_bar
            bot = m.h - m.c >= p["close_pos"] * rng_bar
            ok_l = (t == 1) if p["trend_filter"] else np.ones(m.n, dtype=bool)
            ok_s = (t == -1) if p["trend_filter"] else np.ones(m.n, dtype=bool)
            bl = in_win & ok_l & (m.c > hi) & (body >= strong) & top & (rng_bar > 0)
            bs = in_win & ok_s & (m.c < lo) & (-body >= strong) & bot & (rng_bar > 0)
            side[bl], tag[bl] = 1, 0
            side[bs], tag[bs] = -1, 1
        if mode in ("pullback", "both"):
            ema = m.ema(int(p["pull_ema"]))
            band = p["band_atr"] * atr
            lb = int(p["ext_lookback"])
            ext_up = ind.shift(ind.rolling_max(m.h - ema, lb), 1)
            ext_dn = ind.shift(ind.rolling_max(ema - m.l, lb), 1)
            min_ext = p["min_ext_atr"] * atr
            pl = (in_win & (t == 1) & (m.l <= ema + band) & (m.c > ema) & (body > 0) & (ext_up >= min_ext)
                  & (side == 0))
            ps = (in_win & (t == -1) & (m.h >= ema - band) & (m.c < ema) & (body < 0) & (ext_dn >= min_ext)
                  & (side == 0))
            side[pl], tag[pl] = 1, 2
            side[ps], tag[ps] = -1, 3

    cool = int(p["cooldown_bars"])
    last = -10 ** 9
    for i in np.flatnonzero(side != 0):
        if i - last < cool or not spread_ok(m, i, p["max_spread"]):
            continue
        a = atr[i]
        if a != a:
            continue
        s = int(side[i])
        risk = max(p["stop_atr"] * a, p["min_stop"])
        if (m.spread[i] + p["cost_allow"]) / risk > p["max_cost_frac"]:
            continue
        stop = m.c[i] - s * risk
        target = m.c[i] + s * p["rr"] * risk
        if sigs.add(i, s, stop, target, max_bars=int(p["max_hold_bars"]), tag=int(tag[i])):
            last = i
    return sigs
