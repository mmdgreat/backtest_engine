"""S4 Donchian / H4 Breakout - settings. Tune here; strategy.py holds the rules.

Overrides for a single run without editing this file:  python run.py --set channel=55 --set atr_mult=4
This is a slow trend follower: expect few trades per year, so it needs years of data to judge.
"""
NAME = "s4_donchian_h4"
TITLE = "S4 Donchian H4 Breakout"
MAX_TRADES_PER_DAY = 1
FLATTEN_GAP_SEC = None          # trades are allowed to ride through weekends (swap is charged for each night)

PARAMS = {
    "channel": 20,                  # Donchian channel length in H4 bars (20 = about 3.3 trading days)
    "atr_len": 14,                  # ATR length on H4 bars
    "atr_mult": 3.0,                # initial stop AND chandelier trail distance, in H4 ATRs
    "ema_filter": 200,              # trade only with the H4 EMA of this length (0 = no filter)
    "allow_long": True,
    "allow_short": True,
    "max_spread": 0.60,             # skip entries when the bar's spread (price units) is wider
    "max_hold_days": 10.0,          # time stop in days
}

GRID = {
    "channel": [20, 55],
    "atr_mult": [2.5, 3.0, 4.0],
    "ema_filter": [0, 200],
}
