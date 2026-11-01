"""S6 Volatility Squeeze Breakout.

mode "squeeze": on completed `tf_min` bars, a SQUEEZE is Bollinger Bands entirely inside Keltner Channels. After
a squeeze of at least min_squeeze bars RELEASES, the first bar within follow_bars bars that closes beyond the
previous bar's extreme AND on the same side of the Bollinger mid-line is the breakout signal (up = long).
mode "nr7": after a daily bar with the narrowest range of the last 7, the first M5 close beyond its high (long)
or low (short) on the next trading day, inside the New York window, is the signal.
Stop = stop_atr x ATR (squeeze) or the NR7 range side; target = rr x stop; flat before the rollover."""
import numpy as np

from botcore import indicators as ind
from botcore.signals import SignalSet
from botcore.util import exit_ts_at, hhmm, htf_bar_is_full, spread_ok

TAGS = ["long", "short"]


def _squeeze_signals(m, p, sigs):
    ht = m.htf(int(p["tf_min"]) * 60)
    mid, bu, bl = ind.bollinger(ht.c, int(p["bb_len"]), p["bb_k"])
    _, ku, kl = ind.keltner(ht.h, ht.l, ht.c, int(p["kc_len"]), p["kc_mult"])
    atr = ind.atr(ht.h, ht.l, ht.c, int(p["atr_len"]))
    with np.errstate(invalid="ignore"):
        sq = (bu < ku) & (bl > kl)
    w0, w1 = hhmm(p["window_ny"][0]), hhmm(p["window_ny"][1])
    flat = hhmm(p["flat_ny"])
    max_bars = int(p["hold_bars_htf"] * ht.sec / m.tf_sec)
    run, armed = 0, 0
    for k in range(1, ht.n):
        if sq[k]:
            run += 1
            armed = 0
            continue
        if run >= int(p["min_squeeze"]):
            armed = int(p["follow_bars"])
        run = 0
        if armed <= 0:
            continue
        armed -= 1
        if not ht.complete[k] or not htf_bar_is_full(m, ht, k):
            continue
        i = int(ht.last[k])
        a, c = atr[k], ht.c[k]
        if i >= m.n - 1 or a != a or not (w0 <= m.ny_min[i] < w1) or not spread_ok(m, i, p["max_spread"]):
            continue
        side = 1 if (c > mid[k] and c > ht.h[k - 1]) else (-1 if (c < mid[k] and c < ht.l[k - 1]) else 0)
        if side == 0:
            continue
        risk = p["stop_atr"] * a
        if sigs.add(i, side, c - side * risk, c + side * p["rr"] * risk,
                    exit_ts=exit_ts_at(m, i, "ny", flat), max_bars=max_bars, tag=0 if side > 0 else 1):
            armed = 0


def _nr7_signals(m, p, sigs):
    d1 = m.htf(86400)
    rng = d1.h - d1.l
    look = int(p["nr7_lookback"])
    rmin = ind.rolling_min(rng, look)
    w0, w1 = hhmm(p["window_ny"][0]), hhmm(p["window_ny"][1])
    flat = hhmm(p["flat_ny"])
    for k in range(look, d1.n - 1):
        if not d1.complete[k] or rng[k] != rmin[k]:
            continue
        if d1.start_ts[k + 1] - d1.start_ts[k] > 3 * 86400:      # data hole or long holiday: skip
            continue
        hi, lo = d1.h[k], d1.l[k]
        idx = np.arange(d1.first[k + 1], d1.last[k + 1] + 1)
        idx = idx[(m.ny_min[idx] >= w0) & (m.ny_min[idx] < w1)]
        idx = idx[idx < m.n - 1]
        if idx.size == 0:
            continue
        cc = m.c[idx]
        up_hit, dn_hit = np.flatnonzero(cc > hi), np.flatnonzero(cc < lo)
        pu = up_hit[0] if up_hit.size else 10 ** 9
        pd_ = dn_hit[0] if dn_hit.size else 10 ** 9
        if min(pu, pd_) == 10 ** 9:
            continue
        side, i = (1, int(idx[pu])) if pu < pd_ else (-1, int(idx[pd_]))
        if not spread_ok(m, i, p["max_spread"]):
            continue
        c = m.c[i]
        far = lo if side > 0 else hi
        stop = far if p["nr7_stop"] == "opposite" else (hi + lo) / 2.0
        risk = side * (c - stop)
        sigs.add(i, side, stop, c + side * p["rr"] * risk if risk > 0 else np.nan,
                 exit_ts=exit_ts_at(m, i, "ny", flat), max_bars=288, tag=0 if side > 0 else 1)


def build_signals(m, p):
    sigs = SignalSet(m, tags=TAGS)
    if p["mode"] == "squeeze":
        _squeeze_signals(m, p, sigs)
    elif p["mode"] == "nr7":
        _nr7_signals(m, p, sigs)
    else:
        raise ValueError("mode must be 'squeeze' or 'nr7'")
    return sigs
