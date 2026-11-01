"""S3 Trend Pullback - settings. Tune here; strategy.py holds the rules.

Overrides for a single run without editing this file:  python run.py --set stop_atr=2.0 --set rr=2.5
"""
NAME = "s3_trend_pullback"
TITLE = "S3 Trend Pullback"
MAX_TRADES_PER_DAY = 3
FLATTEN_GAP_SEC = 1800

PARAMS = {
    "h1_fast": 50,                  # H1 EMA lengths that define the trend
    "h1_slow": 200,
    "slope_bars": 3,                # the fast H1 EMA must be rising (long) / falling (short) over this many H1 bars
    "pull_ema": 20,                 # M5 EMA the pullback must reach
    "band_atr": 0.25,               # ... touching within this many ATRs of the EMA counts as a pullback
    "ext_lookback": 24,             # before the pullback, price must have been extended from the EMA within 24 bars
    "min_ext_atr": 1.0,             # ... by at least this many ATRs (so it is a pullback, not a drift along the EMA)
    "atr_len": 14,
    "stop_atr": 1.5,                # stop distance in ATRs from entry
    "rr": 2.0,                      # target = rr x stop distance (0 = no target, use the trail only)
    "trail_atr": 0.0,               # chandelier trail distance in ATRs (0 = off)
    "window_ny": ["03:00", "12:00"],   # only enter inside this New York window (London + NY morning)
    "cooldown_bars": 12,            # bars to wait after a signal before the next one (1 hour on M5)
    "max_spread": 0.40,             # skip entries when the bar's spread (price units) is wider
    "max_hold_bars": 96,            # time stop: 96 M5 bars = 8 hours
    "flat_ny": "16:30",             # always flat by this New York time
}

GRID = {
    "pull_ema": [20, 50],
    "stop_atr": [1.0, 1.5, 2.0],
    "rr": [1.5, 2.0, 3.0],
}
