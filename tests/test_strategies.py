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

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from botcore.data import Market  # noqa: E402
from botcore.synthetic import make  # noqa: E402

STRATS = ["s1_orb", "s2_liquidity_sweep", "s3_trend_pullback", "s4_donchian_h4", "s5_mean_reversion",
          "s6_squeeze_breakout"]
CASES = [(s, {}) for s in STRATS] + [("s6_squeeze_breakout", {"mode": "nr7"})]
MARGIN_BARS = 3 * 288


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
    print(f"\n{len(CASES)} strategy checks passed")


if __name__ == "__main__":
    main()
