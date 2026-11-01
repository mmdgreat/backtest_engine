"""Synthetic XAUUSD M5 candles (broker server clock) for testing the code offline.

A random walk with realistic session volatility, spreads and market hours. With the default trend=0.0 it
contains NO edge, so a sound strategy should NOT look profitable on it: use it to check that the code runs,
is causal, and that the engine is not biased in favour of any strategy (the negative control).
trend > 0 plants persistent momentum (hours to days), which trend followers SHOULD profit from (the positive
control, e.g. trend=0.3)."""
import numpy as np
import pandas as pd

from .data import Market
from .sessions import time_features


def make(start="2024-11-15", days=700, seed=1, start_price=2560.0, trend=0.0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=days, freq="D")
    times = []
    for d in dates:
        if d.dayofweek > 4:
            continue
        t0 = d + pd.Timedelta(hours=0 if d.dayofweek == 0 else 1)
        times.append(pd.date_range(t0, d + pd.Timedelta(hours=23, minutes=55), freq="5min"))
    idx = times[0].append(times[1:]) if len(times) > 1 else times[0]
    ts = ((idx - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")
    f = time_features(ts)
    n = len(ts)

    sess = np.full(n, 0.8)
    sess[(f["utc_min"] < 360)] = 0.6
    sess[(f["ldn_min"] >= 480) & (f["ldn_min"] < 600)] = 2.0
    sess[(f["ldn_min"] >= 600) & (f["ldn_min"] < 720)] = 1.4
    sess[(f["ny_min"] >= 510) & (f["ny_min"] < 630)] = 2.3
    sess[(f["ny_min"] >= 630) & (f["ny_min"] < 780)] = 1.5
    sess[(f["ny_min"] >= 780) & (f["ny_min"] < 960)] = 1.0

    # slowly changing volatility regime; the persistent drift is planted only when trend > 0
    vol_reg = np.exp(np.cumsum(rng.normal(0, 0.01, n)) * 0.15)
    vol_reg = vol_reg / vol_reg.mean()
    drift = np.zeros(n)
    for k in range(1, n):
        drift[k] = 0.995 * drift[k - 1] + rng.normal(0, 0.02)
    sigma_rel = 0.00030 * sess * vol_reg
    ret = drift * sigma_rel * trend + rng.normal(0, 1, n) * sigma_rel
    close = start_price * np.exp(np.cumsum(ret))
    open_ = np.concatenate(([start_price], close[:-1]))
    px = close
    ext_hi = np.abs(rng.normal(0, 0.45, n)) * sigma_rel * px
    ext_lo = np.abs(rng.normal(0, 0.45, n)) * sigma_rel * px
    high = np.maximum(open_, close) + ext_hi
    low = np.minimum(open_, close) - ext_lo

    spread = np.full(n, 18.0)
    spread[(f["ldn_min"] >= 480) & (f["ldn_min"] < 495)] *= 1.6
    spread[(f["ny_min"] >= 510) & (f["ny_min"] < 525)] *= 1.8
    first_hour = (ts % 86400) < 3600 * 1.5
    spread[first_hour] *= 2.0
    spike = rng.random(n) < 0.01
    spread[spike] *= 3.0
    spread = np.round(spread + rng.normal(0, 1.5, n)).clip(8)

    tick = np.round(200 + 400 * np.abs(ret) / np.maximum(sigma_rel, 1e-9) + rng.normal(0, 40, n)).clip(10)
    return pd.DataFrame({
        "time": idx, "open": np.round(open_, 2), "high": np.round(high, 2), "low": np.round(low, 2),
        "close": np.round(close, 2), "tick_volume": tick.astype(int), "spread": spread.astype(int),
    })


def synthetic(days=12, seed=1, start="2025-03-03"):
    """A ready-made Market for tests."""
    return Market(make(start=start, days=days, seed=seed))
