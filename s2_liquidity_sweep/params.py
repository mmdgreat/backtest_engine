"""S2 Liquidity Sweep + Reversal - settings. Tune here; strategy.py holds the rules.

Overrides for a single run without editing this file:  python run.py --set rr=3 --set sweep_min_atr=0.25
"""
NAME = "s2_liquidity_sweep"
TITLE = "S2 Liquidity Sweep + Reversal"
MAX_TRADES_PER_DAY = 2
FLATTEN_GAP_SEC = 1800

PARAMS = {
    "levels": ["asia", "prev_day", "london"],   # liquidity pools to watch (any subset)
    "asia_end_london": "07:00",     # Asian range = 00:00 -> this time, London clock; usable after it ends
    "london_end": "12:00",          # London range = asia_end -> this time; usable after it ends (for NY sweeps)
    "min_day_bars": 100,            # a previous day with fewer M5 bars than this is ignored (holiday stub)
    "kill_london": ["07:00", "11:00"],   # sweeps only count inside these windows (London clock)
    "kill_ny": ["08:00", "12:00"],       # ... and these (New York clock)
    "atr_len": 14,
    "sweep_min_atr": 0.15,          # price must push this many ATRs beyond the level (a real sweep, not a touch)
    "max_return_bars": 3,           # ... and close back inside within this many bars (else it is a breakout)
    "swing_k": 3,                   # a swing point has k lower highs / higher lows each side (M5)
    "max_shift_bars": 24,           # the structure shift must come within this many bars of the sweep
    "sl_buf_atr": 0.25,             # stop sits this many ATRs beyond the sweep extreme
    "rr": 2.0,                      # target = rr x the stop distance
    "max_hold_bars": 48,
    "flat_ny": "16:30",
}

GRID = {
    "sweep_min_atr": [0.1, 0.25],
    "max_shift_bars": [12, 24],
    "sl_buf_atr": [0.15, 0.4],
    "rr": [1.5, 2.0, 3.0],
}
