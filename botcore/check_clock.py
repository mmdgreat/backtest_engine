"""Check that the broker clock follows the 'New York close' convention (server = NY + 7h all year).

    python -m botcore.check_clock --source mongo      (or --source csv --csv candles.csv)

Gold reopens at 18:00 New York after the daily break and on Sunday evening. If the broker's server clock follows
New York time with a fixed offset, those reopenings land on the SAME server time in winter and summer (01:00 for
server = NY + 7h). If they shift by one hour between seasons, the server follows another rule and session logic
(London / New York windows) would be an hour off for half the year.

A handful of odd gaps (data holes, halts) are normal and ignored: the verdict looks at the dominant time."""
import argparse
from collections import Counter

import numpy as np
import pandas as pd

from .data import load_market

MIN_SHARE = 0.95      # the dominant reopen time must account for at least this share of reopenings
MIN_WEEKENDS = 20     # fewer weekends than this (about 5 months) is too little to judge


def _hours(tod):
    h, m = tod.split(":")
    return int(h) + int(m) / 60.0


def verdict(weekly, daily, season_weekly, season_daily):
    """Pure decision function. Returns (status, message); status is OK, CHECK or UNKNOWN."""
    nw, nd = sum(weekly.values()), sum(daily.values())
    if nw < MIN_WEEKENDS:
        return "UNKNOWN", (f"only {nw} weekend reopenings found; at least {MIN_WEEKENDS} (about 5 months of data) "
                           "are needed to judge the clock")
    w_top, w_n = weekly.most_common(1)[0]
    d_top, d_n = daily.most_common(1)[0] if nd else (None, 0)
    problems = []
    if w_n / nw < MIN_SHARE:
        problems.append(f"the weekend reopen time varies (only {w_n} of {nw} at {w_top})")
    if nd and d_n / nd < MIN_SHARE:
        problems.append(f"the daily reopen time varies (only {d_n} of {nd} at {d_top})")
    for name, per_season in (("weekend reopen", season_weekly), ("daily reopen", season_daily)):
        tops = {s: c.most_common(1)[0][0] for s, c in per_season.items() if sum(c.values()) >= 5}
        if len(set(tops.values())) > 1:
            problems.append(f"the {name} time differs between seasons: {tops}")
    if problems:
        return "CHECK", ("; ".join(problems) + ". If it moves by 1h between winter and summer the server does NOT "
                         "follow the New York close rule, and session windows would be off by an hour half the year.")
    ref = d_top or w_top
    offset = (_hours(ref) - 18) % 24
    share = 100.0 * (d_n / nd if nd else w_n / nw)
    if abs(offset - round(offset)) < 1e-9 and round(offset) == 7:
        return "OK", (f"reopenings sit at a constant server time ({ref}, {share:.1f}% of cases) in both seasons. "
                      "That is 18:00 New York with server = NY + 7h, so the convention holds.")
    return "CHECK", (f"reopenings sit at a constant server time ({ref}) in both seasons, so the clock follows New York "
                     f"with a fixed offset, but not +7h: assuming gold reopens at 18:00 New York the offset is "
                     f"NY + {offset:g}h. Set SERVER_MINUS_NY_HOURS = {offset:g} in botcore/settings.py (and "
                     "check the result with a second look at the data) before trusting any session logic.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["mongo", "csv"], default="mongo")
    ap.add_argument("--csv")
    a = ap.parse_args()
    m = load_market(a.source, a.csv)
    ts = m.ts
    gaps = np.diff(ts)
    idx = np.flatnonzero(gaps > 1800)
    weekly, daily = Counter(), Counter()
    seasons = ("winter(Nov-Mar)", "summer(Apr-Oct)")
    season_weekly = {s: Counter() for s in seasons}
    season_daily = {s: Counter() for s in seasons}
    for k in idx:
        g = gaps[k]
        t_open = pd.Timestamp(int(ts[k + 1]), unit="s")
        tod = f"{t_open.hour:02d}:{t_open.minute:02d}"
        season = seasons[1] if 4 <= t_open.month <= 10 else seasons[0]
        if g > 36 * 3600:
            weekly[tod] += 1
            season_weekly[season][tod] += 1
        elif g < 4 * 3600:
            daily[tod] += 1
            season_daily[season][tod] += 1
    print(f"Data: {m.describe()}")
    print("Weekend reopen times (server clock):", dict(weekly.most_common(5)))
    print("Bar time right after the daily break:", dict(daily.most_common(5)))
    for s in seasons:
        print(f"{s}: weekend {dict(season_weekly[s].most_common(3))} | daily {dict(season_daily[s].most_common(3))}")
    for name, c in (("weekend", weekly), ("daily", daily)):
        if c:
            top = c.most_common(1)[0][0]
            odd = {t: n for t, n in c.items() if t != top}
            if odd:
                print(f"Isolated odd {name} gaps (data holes or halts, not a clock problem): {odd}")
    status, msg = verdict(weekly, daily, season_weekly, season_daily)
    print()
    print(f"{status}: {msg}")


if __name__ == "__main__":
    main()
