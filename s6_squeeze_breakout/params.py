"""S6 Volatility Squeeze Breakout - settings. Tune here; strategy.py holds the rules.

Two modes (switch with --set mode=nr7):
  "squeeze"  Bollinger Bands inside Keltner Channels on `tf_min` bars, trade the release
  "nr7"      the day after a Narrowest-Range-of-7 daily bar, trade the break of its high/low
Overrides for a single run:  python run.py --set tf_min=60 --set min_squeeze=8
"""
NAME = "s6_squeeze_breakout"
TITLE = "S6 Volatility Squeeze Breakout"
MAX_TRADES_PER_DAY = 2
FLATTEN_GAP_SEC = 1800

PARAMS = {
    "mode": "squeeze",
    # --- squeeze mode ---
    "tf_min": 15,                   # bar size for the squeeze in minutes (15 or 60)
    "bb_len": 20,
    "bb_k": 2.0,                    # Bollinger width
    "kc_len": 20,
    "kc_mult": 1.5,                 # Keltner width in ATRs; squeeze = Bollinger fully inside Keltner
    "min_squeeze": 6,               # bars the squeeze must last before its release counts
    "follow_bars": 3,               # a confirmed breakout must come within this many bars of the release
    "atr_len": 14,
    "stop_atr": 1.5,                # stop distance in ATRs of the squeeze timeframe
    "rr": 2.0,                      # target = rr x stop distance
    "hold_bars_htf": 8,             # time stop, in squeeze-timeframe bars
    # --- nr7 mode ---
    "nr7_lookback": 7,              # a day is NR7 when its range is the smallest of the last 7 days
    "nr7_stop": "opposite",         # "opposite" = far side of the NR7 range | "mid" = middle of the NR7 range
    # --- both modes ---
    "window_ny": ["03:00", "12:00"],   # only enter inside this New York window
    "max_spread": 0.40,
    "flat_ny": "16:30",
}

GRID = {
    "tf_min": [15, 60],
    "min_squeeze": [4, 6, 10],
    "rr": [1.5, 2.0, 3.0],
}
