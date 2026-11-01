"""Indicators (numpy / pandas, causal: value at index i uses data up to and including i)."""
import numpy as np
import pandas as pd


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def rolling_std(x, n):
    return pd.Series(x).rolling(n, min_periods=n).std(ddof=0).to_numpy()


def true_range(h, l, c):
    prev = np.concatenate(([c[0]], c[:-1]))
    return np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))


def atr(h, l, c, n=14):
    """Wilder ATR."""
    tr = true_range(h, l, c)
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def rolling_max(x, n):
    return pd.Series(x).rolling(n, min_periods=n).max().to_numpy()


def rolling_min(x, n):
    return pd.Series(x).rolling(n, min_periods=n).min().to_numpy()


def shift(x, k=1, fill=np.nan):
    out = np.full(len(x), fill, dtype=float)
    if k > 0:
        out[k:] = x[:-k]
    elif k == 0:
        out[:] = x
    return out


def bollinger(c, n=20, k=2.0):
    mid = sma(c, n)
    sd = rolling_std(c, n)
    return mid, mid + k * sd, mid - k * sd


def keltner(h, l, c, n=20, mult=1.5):
    mid = ema(c, n)
    a = atr(h, l, c, n)
    return mid, mid + mult * a, mid - mult * a


def efficiency_ratio(c, n=48):
    """Kaufman efficiency ratio: ~1 in a clean trend, ~0 in chop."""
    net = np.abs(c - shift(c, n))
    path = pd.Series(np.abs(np.diff(c, prepend=c[0]))).rolling(n, min_periods=n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(path > 0, net / path, np.nan)


def fractal_swings(h, l, n=2):
    """Boolean arrays marking swing highs / lows at index k (needs n bars on each side, so a swing
    at k is only KNOWN once bar k+n has closed). is_sh[k]: h[k] is above the n bars each side."""
    N = len(h)
    is_sh = np.zeros(N, dtype=bool)
    is_sl = np.zeros(N, dtype=bool)
    if N < 2 * n + 1:
        return is_sh, is_sl
    for k in range(n, N - n):
        left_h, right_h = h[k - n:k], h[k + 1:k + n + 1]
        left_l, right_l = l[k - n:k], l[k + 1:k + n + 1]
        if h[k] > left_h.max() and h[k] >= right_h.max():
            is_sh[k] = True
        if l[k] < left_l.min() and l[k] <= right_l.min():
            is_sl[k] = True
    return is_sh, is_sl
