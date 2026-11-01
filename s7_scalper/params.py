"""S7 Scalper (M1) - settings. Tune here; strategy.py holds the rules.

This bot runs on M1 candles (TIMEFRAME below). Overrides for one run without editing this file:
    python run.py --research --set mode=pullback --set stop_atr=2.0
    python run.py --research --set windows_ny=03:00-05:00,08:00-10:30
"""
NAME = "s7_scalper"
TITLE = "S7 Scalper (M1)"
TIMEFRAME = "M1"
MAX_TRADES_PER_DAY = 8
FLATTEN_GAP_SEC = 1800

PARAMS = {
    "mode": "breakout",             # breakout | pullback | both  (breakout wins if both fire on one bar)
    "windows_ny": [["03:00", "05:00"], ["08:00", "10:30"]],   # New York clock: London open, New York open
    "atr_len": 14,                  # M1 ATR length
    # --- breakout mode: a strong M1 bar that closes beyond the last range_bars bars' extreme ---
    "range_bars": 20,
    "body_atr": 0.8,                # signal bar body must be at least this many ATRs
    "close_pos": 0.7,               # close must sit in the top (long) / bottom (short) 30% of the bar's range
    "trend_filter": True,           # breakout only with the M5 trend (M5 fast EMA above/below slow and sloping)
    # --- pullback mode: pullback to the M1 EMA inside an M5 trend ---
    "pull_ema": 20,
    "band_atr": 0.25,
    "ext_lookback": 15,
    "min_ext_atr": 1.0,
    # --- M5 trend (used by both modes) ---
    "m5_fast": 20,
    "m5_slow": 50,
    "m5_slope_bars": 3,
    # --- exits and entry discipline ---
    "stop_atr": 1.5,                # stop distance in ATRs ...
    "min_stop": 1.0,                # ... but never closer than this many dollars (1.00 = 100 points)
    "rr": 1.5,                      # target = rr x stop distance
    "max_hold_bars": 15,            # time stop in M1 bars (minutes)
    "cooldown_bars": 10,            # minutes to wait after a signal
    "max_spread": 0.30,             # skip entries when the bar's spread (price units) is wider
    "cost_allow": 0.15,             # allowance for slippage added to the spread when estimating the round-trip cost
    "max_cost_frac": 0.25,          # skip when (spread + cost_allow) is more than this share of the stop distance
}

GRID = {
    "stop_atr": [1.0, 1.5, 2.0],
    "rr": [1.0, 1.5, 2.0],
    "max_hold_bars": [10, 20],
}
