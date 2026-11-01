"""Strategy tests: every strategy must (1) produce signals and (2) be free of look-ahead.

Look-ahead check: build signals on the full data and on a copy cut off at a random bar. Signals on the part
the two share (except the last 3 days, where the cut can legitimately hide a half-formed higher-timeframe bar)
must be identical. If a strategy peeked at the future, the cut copy would give different signals.

Run:  python tests/test_strategies.py
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from botcore.data import Market  # noqa: E402
from botcore.sessions import time_features  # noqa: E402
from botcore.synthetic import make  # noqa: E402

STRATS = ["s1_orb", "s2_liquidity_sweep", "s3_trend_pullback", "s4_donchian_h4", "s5_mean_reversion",
          "s6_squeeze_breakout"]
CASES = [(s, {}) for s in STRATS] + [("s6_squeeze_breakout", {"mode": "nr7"})]
MARGIN_BARS = 3 * 288
M1_CASES = [("s7_scalper", {"mode": m}) for m in ("breakout", "pullback", "both")]
M1_MARGIN_BARS = 3 * 1440


def make_m1(days=90, seed=5, start_price=2560.0, start="2025-01-06"):
    """Synthetic M1 candles (random walk, busier at the London and New York opens). Offline code checks only."""
    rng = np.random.default_rng(seed)
    parts = []
    for d in pd.date_range(start, periods=days, freq="D"):
        if d.dayofweek > 4:
            continue
        parts.append(pd.date_range(d + pd.Timedelta(hours=0 if d.dayofweek == 0 else 1),
                                   d + pd.Timedelta(hours=23, minutes=59), freq="1min"))
    idx = parts[0].append(parts[1:])
    ts = ((idx - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")
    f = time_features(ts)
    n = len(ts)
    sess = np.full(n, 0.7)
    sess[(f["ny_min"] >= 180) & (f["ny_min"] < 300)] = 1.8
    sess[(f["ny_min"] >= 480) & (f["ny_min"] < 630)] = 2.2
    drift = np.zeros(n)
    for k in range(1, n):
        drift[k] = 0.98 * drift[k - 1] + rng.normal(0, 0.05)
    sigma = 0.00009 * sess
    ret = (drift * 0.4 + rng.normal(0, 1, n)) * sigma
    close = start_price * np.exp(np.cumsum(ret))
    open_ = np.concatenate(([start_price], close[:-1]))
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n)) * sigma * close
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n)) * sigma * close
    spread = np.round(rng.normal(18, 3, n)).clip(8)
    return pd.DataFrame({"time": idx, "open": open_, "high": high, "low": low, "close": close,
                         "tick_volume": rng.integers(20, 300, n), "spread": spread})


def load(folder, fname):
    path = os.path.join(ROOT, folder, fname)
    spec = importlib.util.spec_from_file_location(f"{folder}_{fname[:-3]}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(folder, df, overrides):
    P, S = load(folder, "params.py"), load(folder, "strategy.py")
    p = dict(P.PARAMS)
    p.update(overrides)
    m = Market(df)
    return m, S.build_signals(m, p)


def main():
    df = make("2025-01-06", 330, 7)
    rng = np.random.default_rng(3)
    for folder, ov in CASES:
        m, sig = build(folder, df, ov)
        label = f"{folder}{' ' + str(ov) if ov else ''}"
        assert sig.count() > 0, f"{label}: no signals at all on 330 synthetic days"
        for cut_frac in (0.45, 0.7):
            cut = int(len(df) * cut_frac) + int(rng.integers(0, 288))
            m2, sig2 = build(folder, df.iloc[:cut].reset_index(drop=True), ov)
            limit = min(m.n, m2.n) - MARGIN_BARS
            a, b = sig.side[:limit], sig2.side[:limit]
            assert np.array_equal(a, b), f"{label}: signals changed when future data was removed (look-ahead!)"
            both = a != 0
            assert np.allclose(sig.stop[:limit][both], sig2.stop[:limit][both], equal_nan=True), f"{label}: stops differ"
            assert np.allclose(sig.target[:limit][both], sig2.target[:limit][both], equal_nan=True), \
                f"{label}: targets differ"
        print(f"ok   {label}: {sig.count()} signals, no look-ahead")
    df1 = make_m1()
    for folder, ov in M1_CASES:
        m, sig = build(folder, df1, ov)
        label = f"{folder} {ov} (M1)"
        assert sig.count() > 0, f"{label}: no signals on synthetic M1 data"
        for cut_frac in (0.45, 0.7):
            cut = int(len(df1) * cut_frac) + int(rng.integers(0, 1440))
            m2, sig2 = build(folder, df1.iloc[:cut].reset_index(drop=True), ov)
            limit = min(m.n, m2.n) - M1_MARGIN_BARS
            a, b = sig.side[:limit], sig2.side[:limit]
            assert np.array_equal(a, b), f"{label}: signals changed when future data was removed (look-ahead!)"
            both = a != 0
            assert np.allclose(sig.stop[:limit][both], sig2.stop[:limit][both], equal_nan=True), f"{label}: stops differ"
            assert np.allclose(sig.target[:limit][both], sig2.target[:limit][both], equal_nan=True), \
                f"{label}: targets differ"
        print(f"ok   {label}: {sig.count()} signals, no look-ahead")
    # the scalper must refuse M5 data instead of silently producing meaningless results
    try:
        build("s7_scalper", df, {})
        raise AssertionError("s7_scalper accepted M5 data")
    except SystemExit as e:
        assert "M1" in str(e)
    print("ok   s7_scalper refuses non-M1 data")
    print(f"\n{len(CASES) + len(M1_CASES) + 1} strategy checks passed")


if __name__ == "__main__":
    main()
