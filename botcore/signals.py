"""Signal container. A strategy fills one of these; the engine decides what actually trades.

A signal at base-bar index i is known at the CLOSE of bar i. The engine enters at the OPEN of bar i+1.
Everything a strategy knows at bar i must come from bars <= i."""
import numpy as np


class SignalSet:
    def __init__(self, m, tags=None):
        n = m.n
        self.m = m
        self.side = np.zeros(n, dtype=np.int8)
        self.stop = np.full(n, np.nan)
        self.target = np.full(n, np.nan)
        self.trail = np.full(n, np.nan)       # trailing-stop distance in price units (chandelier)
        self.exit_ts = np.zeros(n, dtype=np.int64)   # forced exit at/after this broker timestamp (0 = none)
        self.max_bars = np.zeros(n, dtype=np.int32)  # forced exit after this many bars (0 = none)
        self.tag = np.zeros(n, dtype=np.int16)
        self.tags = list(tags or ["main"])
        self.rejected = 0

    def add(self, i, side, stop, target=np.nan, trail=np.nan, exit_ts=0, max_bars=0, tag=0):
        """Returns True if stored. A signal whose stop sits on the wrong side of the bar close is dropped."""
        ref = self.m.c[i]
        if side not in (1, -1) or not np.isfinite(stop):
            self.rejected += 1
            return False
        if side * (ref - stop) <= 0:
            self.rejected += 1
            return False
        if np.isfinite(target) and side * (target - ref) <= 0:
            self.rejected += 1
            return False
        self.side[i] = side
        self.stop[i] = stop
        self.target[i] = target
        self.trail[i] = trail
        self.exit_ts[i] = exit_ts
        self.max_bars[i] = max_bars
        self.tag[i] = tag
        return True

    def indices(self):
        return np.flatnonzero(self.side != 0)

    def count(self):
        return int((self.side != 0).sum())
