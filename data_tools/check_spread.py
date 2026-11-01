"""Measure the spread you really pay and compare it with the `spread` stored on each candle.

Run:  python check_spread.py              (the last 5 days)
      python check_spread.py --days 10

The backtest charges the spread stored on each candle (bid -> ask). MT5 keeps one number per bar, which can be
lower than the spread at the moment a trade is filled. This reads the raw ticks for the same days, takes the real
spread at the first tick of every M1 bar (where the backtest fills its entries) and compares it with that bar's
stored spread. Needs MT5 open and logged in, like the other tools here.

If the real spread is wider, run the bots with  python run.py --spread-add X  (X = the number this prints).
"""
import argparse
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
import numpy as np

import config
from mt5_common import connect_mt5

SERVER_MINUS_NY_HOURS = 7     # same assumption as botcore/settings.py; only used to label the hours below
MIN_BARS_PER_HOUR = 30        # hours with fewer bars than this are not printed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5, help="calendar days back from the latest tick")
    args = ap.parse_args()

    connect_mt5()
    point = mt5.symbol_info(config.SYMBOL).point
    tick = mt5.symbol_info_tick(config.SYMBOL)
    if tick is None:
        raise SystemExit(f"No tick for {config.SYMBOL}: {mt5.last_error()}")
    end = datetime.fromtimestamp(tick.time, tz=timezone.utc)
    start = end - timedelta(days=args.days)
    ticks = mt5.copy_ticks_range(config.SYMBOL, start, end, mt5.COPY_TICKS_INFO)
    if ticks is None or len(ticks) == 0:
        raise SystemExit(f"No ticks for {start:%Y-%m-%d}..{end:%Y-%m-%d}: {mt5.last_error()}")
    rates = mt5.copy_rates_range(config.SYMBOL, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) == 0:
        raise SystemExit(f"No M1 bars for {start:%Y-%m-%d}..{end:%Y-%m-%d}: {mt5.last_error()}")
    mt5.shutdown()

    # real spread per tick, grouped into M1 bars (ticks arrive in time order)
    sp = ticks["ask"] - ticks["bid"]
    ok = (ticks["bid"] > 0) & (sp >= 0)
    t = ticks["time"].astype(np.int64)[ok]
    sp = sp[ok]
    bar = t - t % 60
    first = np.flatnonzero(np.r_[True, np.diff(bar) != 0])
    tick_bar = bar[first]
    at_open = sp[first]
    avg_in = np.add.reduceat(sp, first) / np.diff(np.r_[first, len(sp)])

    both, ia, ib = np.intersect1d(tick_bar, rates["time"].astype(np.int64), return_indices=True)
    if both.size == 0:
        raise SystemExit("No M1 bar matched a tick: check that MT5 holds tick history for these days")
    at_open, avg_in = at_open[ia], avg_in[ia]
    stored = rates["spread"].astype(float)[ib] * point
    gap = at_open - stored

    def stamp(ts):
        return f"{datetime.fromtimestamp(int(ts), tz=timezone.utc):%Y-%m-%d %H:%M}"

    def row(name, x):
        return f"  {name:<36}{np.mean(x):>8.3f}{np.median(x):>9.3f}{np.percentile(x, 90):>9.3f}"

    print(f"{config.SYMBOL}: {both.size:,} M1 bars with ticks, {stamp(both[0])} -> {stamp(both[-1])} (server time)")
    print("Spread in price units (0.10 = 10 points = $0.10 per ounce).\n")
    print(f"  {'':<36}{'mean':>8}{'median':>9}{'90th %':>9}")
    print(row("stored on the candle", stored))
    print(row("real, at the bar's first tick", at_open))
    print(row("real, average over the bar's ticks", avg_in))
    print(f"\n  The stored spread is below the real opening spread in {100 * (gap > 1e-9).mean():.1f}% of bars.")

    hour = (both // 3600) % 24
    print(f"\nBy hour (New York = server - {SERVER_MINUS_NY_HOURS}h). S7 trades New York 03:00-05:00 and 08:00-10:30.")
    print(f"  {'server':>6}  {'NY':>5}  {'bars':>6}  {'stored':>7}  {'real':>7}  {'extra':>7}")
    for hr in range(24):
        k = hour == hr
        if k.sum() < MIN_BARS_PER_HOUR:
            continue
        print(f"  {hr:>3}:00  {(hr - SERVER_MINUS_NY_HOURS) % 24:>2}:00  {int(k.sum()):>6,}  "
              f"{stored[k].mean():>7.3f}  {at_open[k].mean():>7.3f}  {gap[k].mean():>+7.3f}")

    extra = float(gap.mean())
    print()
    if extra <= 0.01:
        print("OK: the stored spread matches what you would pay at the bar open. No --spread-add needed.")
    else:
        print(f"CHECK: the real spread at the bar open is {extra:.2f} wider on average than the candles say.")
        print(f"Run the bots with  --spread-add {extra:.2f}  and rerun this on another week to confirm the number.")


if __name__ == "__main__":
    main()
