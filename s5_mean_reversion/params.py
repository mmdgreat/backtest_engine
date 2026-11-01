"""S5 Mean Reversion (Asian session) - settings. Tune here; strategy.py holds the rules.

Overrides for a single run without editing this file:  python run.py --set bb_k=2.5 --set er_max=0.25
Risky around news: the scheduled-news blackout is NOT automatic here (no calendar data); see STRATEGY_RULES.md.
"""
NAME = "s5_mean_reversion"
TITLE = "S5 Mean Reversion (Asian session)"
MAX_TRADES_PER_DAY = 2
FLATTEN_GAP_SEC = 1800

PARAMS = {
    "window_london": ["00:00", "07:00"],   # trade only inside this London-clock window (Asian session)
    "bb_len": 20,                   # Bollinger length on M5 closes
    "bb_k": 2.0,                    # band width in standard deviations
    "atr_len": 14,
    "er_len": 48,                   # efficiency-ratio window (48 M5 bars = 4 hours)
    "er_max": 0.30,                 # only fade when the market is choppy: efficiency ratio below this
    "atr_avg_len": 288,             # one day of M5 bars
    "max_atr_ratio": 1.3,           # skip when ATR is above 1.3x its one-day average (volatility spike)
    "stop_buf_atr": 0.5,            # stop sits this many ATRs beyond the extreme of the last 3 bars
    "min_rr": 0.8,                  # skip when the distance to the mid-band is less than this x the stop distance
    "max_spread": 0.35,             # skip entries when the bar's spread (price units) is wider
    "max_hold_bars": 36,            # time stop: 36 M5 bars = 3 hours
}

GRID = {
    "bb_k": [2.0, 2.5],
    "er_max": [0.2, 0.3, 0.4],
    "stop_buf_atr": [0.3, 0.5, 1.0],
}
