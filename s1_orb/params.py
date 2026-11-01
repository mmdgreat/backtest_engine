"""S1 Opening Range Breakout - settings. Tune here; strategy.py holds the rules.

Overrides for a single run without editing this file:  python run.py --set range_min=60 --set rr=3
"""
NAME = "s1_orb"
TITLE = "S1 Opening Range Breakout"
MAX_TRADES_PER_DAY = 2          # one per session (London, New York)
FLATTEN_GAP_SEC = 1800          # close any trade before a market break longer than 30 min

PARAMS = {
    "sessions": ["london", "ny"],   # which opens to trade
    "london_open": "08:00",         # London local time
    "ny_open": "08:20",             # New York local time (COMEX gold open; use 09:30 for the stock open)
    "range_min": 30,                # opening range length in minutes (30 or 60)
    "entry_window_min": 120,        # a break is only taken within this many minutes after the range ends
    "atr_len": 14,                  # ATR length on M5 bars
    "stop_mode": "atr",             # "atr" = atr_mult x ATR from entry | "range" = opposite side of the range
    "atr_mult": 2.0,                # stop distance in ATRs (stop_mode "atr")
    "rr": 2.0,                      # target = rr x the stop distance
    "min_range_atr": 2.0,           # skip days where the opening range is narrower than this many ATRs
    "max_range_atr": 15.0,          # ... or wider than this many ATRs
    "max_hold_bars": 48,            # time stop: 48 M5 bars = 4 hours
    "flat_ny": "16:30",             # always flat by this New York time (before the 17:00 rollover)
}

# Small on purpose: every extra row you try makes a lucky result more likely.
GRID = {
    "range_min": [30, 60],
    "atr_mult": [1.5, 2.0, 3.0],
    "rr": [1.5, 2.0, 3.0],
}
