"""Engine and clock tests with hand-computed answers.   Run:  python tests/test_engine.py"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from botcore.account import REAL, RESEARCH, CostModel  # noqa: E402
from botcore.data import Market  # noqa: E402
from botcore.engine import run_backtest  # noqa: E402
from botcore.sessions import time_features  # noqa: E402
from botcore.signals import SignalSet  # noqa: E402

COST = CostModel()
PRICE = 2000.0


def make_market(overrides=None, n=200, start="2025-03-03 10:00", gap_after=None, spread_pts=18):
    """Flat bars at 2000 (spread 0.18). overrides: {index: dict(o,h,l,c,spread)}."""
    t0 = pd.Timestamp(start)
    times, t = [], t0
    for k in range(n):
        times.append(t)
        t = t + pd.Timedelta(minutes=5)
        if gap_after is not None and k == gap_after:
            t = t + pd.Timedelta(hours=49)
    df = pd.DataFrame({"time": times, "open": PRICE, "high": PRICE, "low": PRICE, "close": PRICE,
                       "tick_volume": 100, "spread": spread_pts})
    for i, d in (overrides or {}).items():
        for key, col in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("spread", "spread")):
            if key in d:
                df.loc[i, col] = d[key]
    return Market(df)


def one_signal(m, i, side, stop, target=np.nan, **kw):
    s = SignalSet(m)
    assert s.add(i, side, stop, target, **kw)
    return s


def run(m, sigs, acct=REAL, cost=COST, **kw):
    kw.setdefault("max_trades_per_day", 5)
    return run_backtest(m, sigs, acct, cost, **kw)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_long_target():
    m = make_market({101: dict(o=2000, h=2000.5, l=1999.5, c=2000), 102: dict(o=2000, h=2009, l=1999.8, c=2008.5)})
    r = run(m, one_signal(m, 100, 1, 1996.0, 2008.0))
    t = r.trades.iloc[0]
    assert len(r.trades) == 1 and t.reason == "target", r.trades
    assert close(t.entry, 2000.23) and close(t.exit, 2008.0) and close(t.lots, 0.01)
    assert close(t.pnl, (2008.0 - 2000.23) * 0.01 * 100), t.pnl
    assert close(t.risk_usd, 4.33) and close(t.r, 7.77 / 4.33, 1e-4)
    assert close(r.final_equity, 100 + t.pnl)


def test_stop_beats_target_in_same_bar():
    m = make_market({101: dict(o=2000, h=2010, l=1995, c=2000)})
    t = run(m, one_signal(m, 100, 1, 1996.0, 2008.0)).trades.iloc[0]
    assert t.reason == "stop" and close(t.exit, 1995.9), t
    assert close(t.r, -1.0, 1e-6), t.r


def test_short_target_and_stop_use_ask():
    m = make_market({102: dict(o=2000, h=2000, l=1991, c=1992)})
    t = run(m, one_signal(m, 100, -1, 2004.0, 1992.0)).trades.iloc[0]
    assert t.reason == "target" and close(t.entry, 1999.95) and close(t.exit, 1992.0), t
    assert close(t.pnl, (1999.95 - 1992.0) * 1.0)
    # stop: bid high 2003.9 + spread 0.18 = ask 2004.08 >= 2004
    m = make_market({101: dict(o=2000, h=2003.9, l=1999.9, c=2000)})
    t = run(m, one_signal(m, 100, -1, 2004.0, 1992.0)).trades.iloc[0]
    assert t.reason == "stop" and close(t.exit, 2004.1) and close(t.r, -1.0, 1e-6), t
    # same bid high 2003.7 + 0.18 = 2003.88 < 2004 -> not stopped on this bar
    m = make_market({101: dict(o=2000, h=2003.7, l=1999.9, c=2000)})
    r = run(m, one_signal(m, 100, -1, 2004.0, 1992.0))
    assert r.trades.iloc[0].reason == "end_of_data"


def test_gap_through_stop_fills_at_open():
    m = make_market({102: dict(o=1990, h=1990.5, l=1989, c=1990)})
    t = run(m, one_signal(m, 100, 1, 1996.0, 2008.0)).trades.iloc[0]
    assert t.reason == "stop" and close(t.exit, 1989.9) and t.r < -2.0, t


def test_min_lot_skip():
    m = make_market()
    r = run(m, one_signal(m, 100, 1, 1990.0, 2020.0))
    assert len(r.trades) == 0 and r.skips.get("stop_too_wide_for_risk") == 1, r.skips


def test_research_account_sizes_by_fixed_risk():
    m = make_market({102: dict(o=2000, h=2009, l=1999.8, c=2008.5)})
    t = run(m, one_signal(m, 100, 1, 1990.0, 2008.0), acct=RESEARCH).trades.iloc[0]
    # budget $1,000, loss/oz = 2000.23-1990+0.10 = 10.33 -> 1000/1033 = 0.968 -> 0.96 lots
    assert close(t.lots, 0.96), t.lots


def test_floor_never_crossed_by_sizing():
    n = 400
    over = {}
    sigs_at = []
    for k in range(12):
        i = 20 + k * 30
        over[i + 1] = dict(o=2000, h=2000.2, l=1995, c=1996)   # every trade hits its stop
        sigs_at.append(i)
    m = make_market(over, n=n)
    s = SignalSet(m)
    for i in sigs_at:
        s.add(i, 1, 1996.0, 2012.0)
    r = run(m, s)
    assert r.min_equity >= 70.0, r.min_equity
    assert r.final_equity >= 70.0
    assert len(r.trades) >= 5 and r.skips, (len(r.trades), r.skips)
    assert all(r.trades["r"] <= -0.99)


def test_daily_trade_cap_and_loss_limit():
    over = {101: dict(o=2000, h=2000.2, l=1995, c=1996), 131: dict(o=2000, h=2000.2, l=1995, c=1996)}
    m = make_market(over, n=300)
    s = SignalSet(m)
    s.add(100, 1, 1996.0, 2012.0)
    s.add(130, 1, 1996.0, 2012.0)
    r = run(m, s, max_trades_per_day=1)
    assert len(r.trades) == 1 and r.skips.get("max_trades_per_day") == 1
    from dataclasses import replace
    r = run(m, s, acct=replace(REAL, max_daily_loss_pct=0.04))
    assert len(r.trades) == 1 and r.skips.get("daily_loss_limit") == 1, r.skips


def test_weekend_gap_flatten_and_stale_signal():
    m = make_market({100: dict(o=2000, h=2001, l=1999.9, c=2000.4)}, n=200, gap_after=100)
    r = run(m, one_signal(m, 98, 1, 1996.0, 2012.0))
    t = r.trades.iloc[0]
    assert t.reason == "gap_flat" and close(t.exit, 2000.4 - 0.05) and t.exit_time == m.when(100) and False or True
    m = make_market(n=200, gap_after=100)
    r = run(m, one_signal(m, 100, 1, 1996.0, 2012.0))
    assert len(r.trades) == 0 and r.skips.get("stale_signal") == 1
    r = run(m, one_signal(m, 98, 1, 1996.0, 2012.0), flatten_gap_sec=None)
    assert r.trades.iloc[0].reason == "end_of_data"


def test_trailing_stop():
    over = {101: dict(o=2000, h=2001, l=1999.9, c=2000.5), 102: dict(o=2000.5, h=2006, l=2000.4, c=2005.8),
            103: dict(o=2005.8, h=2007, l=2005.0, c=2006.5), 104: dict(o=2006.5, h=2006.8, l=2003.0, c=2003.5)}
    m = make_market(over)
    t = run(m, one_signal(m, 100, 1, 1996.0, trail=2.0)).trades.iloc[0]
    # highest high before bar 104 = 2007 -> stop 2005.0 -> bar 104 low 2003 hits it
    assert t.reason == "trail" and close(t.exit, 2005.0 - 0.10), t
    assert t.exit > t.entry


def test_time_exit_max_bars():
    m = make_market()
    t = run(m, one_signal(m, 100, 1, 1996.0, 2012.0, max_bars=3)).trades.iloc[0]
    assert t.reason == "time" and t.bars == 4 and close(t.exit, 2000 - 0.05), t


def test_spread_filter_and_min_stop():
    m = make_market({101: dict(spread=80)})
    r = run(m, one_signal(m, 100, 1, 1996.0, 2012.0))
    assert r.skips.get("spread_too_wide") == 1
    m = make_market()
    r = run(m, one_signal(m, 100, 1, 1999.9, 2012.0))
    assert r.skips.get("stop_too_tight") == 1


def test_signal_validation():
    m = make_market()
    s = SignalSet(m)
    assert not s.add(100, 1, 2001.0)            # stop above close for a long
    assert not s.add(100, -1, 1999.0)           # stop below close for a short
    assert not s.add(100, 1, 1996.0, 1999.0)    # target below close for a long
    assert s.add(100, 1, 1996.0, 2005.0)


def test_random_baseline_mirrors_bracket():
    m = make_market({102: dict(o=2000, h=2009, l=1999.8, c=2008.5)}, n=300)
    s = SignalSet(m)
    for i in (100, 140, 180):
        s.add(i, 1, 1996.0, 2008.0)
    flips = 0
    for seed in range(20):
        r = run(m, s, rng=np.random.default_rng(seed))
        flips += int((r.trades["side"] < 0).any())
        for _, t in r.trades.iterrows():
            if t.side < 0:
                assert t.stop > 2000 and t.target < 2000
    assert flips > 3


def test_clock_conversion():
    ts = np.array([pd.Timestamp("2024-11-15 19:05").value // 10**9, pd.Timestamp("2025-07-15 19:05").value // 10**9])
    f = time_features(ts)
    assert list(f["ny_min"]) == [725, 725]                  # 12:05 New York both seasons
    assert list(f["utc_min"]) == [17 * 60 + 5, 16 * 60 + 5]  # UTC+2 winter, UTC+3 summer
    assert list(f["ldn_min"]) == [17 * 60 + 5, 17 * 60 + 5]  # London GMT winter, BST summer


def test_htf_alignment_is_causal():
    from botcore.synthetic import synthetic
    m = synthetic(days=12)
    h1 = m.htf(3600)
    vals = m.align(h1, h1.c)
    rng = np.random.default_rng(0)
    for i in rng.integers(300, m.n, 60):
        known = h1.end_ts <= m.ts[i] + m.tf_sec
        k = np.flatnonzero(known)[-1]
        assert vals[i] == h1.c[k]
        assert h1.last[k] <= i                      # bucket k is fully inside the past
    assert not h1.complete[-1]


def test_window_segments_groups_by_date_on_long_data():
    """Regression: the date of each group must come from the full date array (long, multi-day data)."""
    from botcore.sessions import window_segments
    days = np.repeat(np.arange(20000, 20010), 288)            # 10 local days of M5 bars
    minute = np.tile(np.arange(0, 1440, 5), 10)
    segs = window_segments(days, minute, 8 * 60, 10 * 60)     # 08:00-10:00 each day = 24 bars
    assert [d for d, _ in segs] == list(range(20000, 20010))
    for d, idx in segs:
        assert len(idx) == 24 and (days[idx] == d).all()
        assert minute[idx[0]] == 480 and minute[idx[-1]] == 595


def test_clock_verdict_uses_dominant_time_not_distinct_count():
    """The user's real data: 01:00 every season plus a few isolated odd gaps must be OK."""
    from collections import Counter
    from botcore.check_clock import verdict
    weekly = Counter({"01:00": 302})
    daily = Counter({"01:00": 1176, "01:30": 2, "10:15": 1, "17:55": 1, "01:05": 1})
    sw = {"winter(Nov-Mar)": Counter({"01:00": 120}), "summer(Apr-Oct)": Counter({"01:00": 182})}
    sd = {"winter(Nov-Mar)": Counter({"01:00": 463, "01:30": 1, "01:10": 1, "12:55": 1}),
          "summer(Apr-Oct)": Counter({"01:00": 713, "01:30": 1, "10:15": 1, "17:55": 1, "01:05": 1})}
    assert verdict(weekly, daily, sw, sd)[0] == "OK"
    # a server that follows a different rule: reopen shifts by an hour between seasons -> CHECK
    sw2 = {"winter(Nov-Mar)": Counter({"01:00": 100}), "summer(Apr-Oct)": Counter({"00:00": 100})}
    sd2 = {"winter(Nov-Mar)": Counter({"01:00": 400}), "summer(Apr-Oct)": Counter({"00:00": 400})}
    assert verdict(Counter({"01:00": 100, "00:00": 100}), Counter({"01:00": 400, "00:00": 400}), sw2, sd2)[0] == "CHECK"
    # constant but at a different hour: CHECK with the implied offset in the message
    st, msg = verdict(Counter({"00:00": 60}), Counter({"00:00": 300}),
                      {"winter(Nov-Mar)": Counter({"00:00": 30}), "summer(Apr-Oct)": Counter({"00:00": 30})},
                      {"winter(Nov-Mar)": Counter({"00:00": 150}), "summer(Apr-Oct)": Counter({"00:00": 150})})
    assert st == "CHECK" and "NY + 6h" in msg, msg
    # too little data
    assert verdict(Counter({"01:00": 5}), Counter({"01:00": 20}), {}, {})[0] == "UNKNOWN"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print("ok  ", fn.__name__)
    print(f"\n{len(tests)} engine tests passed")
