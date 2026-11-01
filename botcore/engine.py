"""Bar-by-bar trade simulator. Frozen: strategies never change how trades are filled.

Rules of the simulation
-----------------------
* A signal at bar i (known at its close) is filled at the OPEN of bar i+1 (market order).
* Candle prices are BID. Longs buy at ask = bid + that bar's spread; shorts sell at bid.
  A short's stop/target are triggered by the ASK (bid + spread).
* Slippage is adverse on market entries/exits and on stop fills; target (limit) fills get none.
* If one bar touches both stop and target, the STOP is assumed to hit first.
* A bar that opens beyond the stop (gap) fills at the open (plus stop slippage), not at the stop.
* One position at a time. A new signal may be taken only after the previous trade has closed.
* Sizing happens at the fill: risk budget = min(risk_pct x equity, equity - floor); lots rounded
  DOWN to the lot step; below the minimum lot the trade is skipped, never forced in.
"""
import math
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

NAN = float("nan")


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    skips: dict
    final_equity: float
    min_equity: float
    halted_at: object
    n_signals: int
    acct: object
    cost: object


def run_backtest(m, sigs, acct, cost, max_trades_per_day=3, flatten_gap_sec=1800,
                 start=0, end=None, rng=None, max_entry_gap_sec=None):
    n = m.n if end is None else min(int(end), m.n)
    P = m.py
    ts, o, h, l, c, sp_raw, sday = P.ts, P.o, P.h, P.l, P.c, P.spread, P.sday
    mult = cost.cost_mult
    slip_m = cost.slippage_market * mult
    slip_s = cost.slippage_stop * mult
    tf = m.tf_sec
    contract = acct.contract_size
    comm_rt = 2.0 * cost.commission_per_lot_per_side

    sidx = sigs.indices()
    sidx = sidx[(sidx >= start) & (sidx < n - 1)]
    nsig = len(sidx)

    equity = acct.initial_capital
    min_eq = equity
    skips = Counter()
    rows = []
    day_start, day_n, day_pnl = {}, {}, {}
    halted_at = None
    cur, ptr = start, 0

    while True:
        while ptr < nsig and sidx[ptr] < cur:
            ptr += 1
        if ptr >= nsig:
            break
        i = int(sidx[ptr])
        ptr += 1
        j = i + 1
        cur = j

        if acct.equity_floor > 0 and equity <= acct.equity_floor + acct.halt_buffer:
            halted_at = ts[i]
            skips["halted"] += nsig - ptr + 1
            break
        if ts[j] - ts[i] > (3 * tf if max_entry_gap_sec is None else max_entry_gap_sec):
            skips["stale_signal"] += 1
            continue
        sd = sday[j]
        if day_n.get(sd, 0) >= max_trades_per_day:
            skips["max_trades_per_day"] += 1
            continue
        if sd in day_start and day_pnl[sd] <= -acct.max_daily_loss_pct * day_start[sd]:
            skips["daily_loss_limit"] += 1
            continue
        spr = sp_raw[j] * mult
        if spr > cost.max_spread:
            skips["spread_too_wide"] += 1
            continue
        ex_ts = int(sigs.exit_ts[i])
        if ex_ts and ts[j] >= ex_ts:
            skips["expired"] += 1
            continue

        side = int(sigs.side[i])
        stop = float(sigs.stop[i])
        target = float(sigs.target[i])
        trail = float(sigs.trail[i])
        if rng is not None and rng.random() < 0.5:      # random-direction baseline: mirror the bracket
            ref = c[i]
            ds = side * (ref - stop)
            dt = side * (target - ref) if target == target else NAN
            side = -side
            stop = ref - side * ds
            target = ref + side * dt if dt == dt else NAN

        entry = o[j] + spr + slip_m if side > 0 else o[j] - slip_m
        dist = entry - stop if side > 0 else stop - entry
        if dist < cost.min_stop:
            skips["stop_too_tight"] += 1
            continue
        if target == target and side * (target - entry) <= 0:
            skips["target_invalid"] += 1
            continue

        # ---- sizing ------------------------------------------------------------------------
        loss_oz = dist + slip_s
        loss_lot = loss_oz * contract + comm_rt
        # Risk never shrinks below the starting-capital amount (a 0.01 lot cannot shrink anyway);
        # it grows with equity once equity is above the start. The floor cap below always applies.
        base = max(equity, acct.initial_capital) if acct.compounding else acct.initial_capital
        pct_budget = acct.risk_pct * base
        room = equity - acct.equity_floor
        budget = min(pct_budget, room)
        if budget <= 0:
            skips["floor_no_room"] += 1
            continue
        lots = math.floor(budget / loss_lot / acct.lot_step + 1e-9) * acct.lot_step
        lots = round(min(lots, acct.max_lot), 8)
        if lots < acct.min_lot - 1e-9:
            skips["floor_no_room" if room < pct_budget else "stop_too_wide_for_risk"] += 1
            continue
        planned_risk = lots * loss_lot

        # ---- walk the position bar by bar --------------------------------------------------
        max_bars = int(sigs.max_bars[i])
        stop0 = stop
        moved = False
        hh, ll = -1e18, 1e18
        x = j
        px, reason = None, None
        swap_oz = 0.0          # swap per ounce while the position is held across the 5pm New York rollover
        swap_rate = cost.swap_long if side > 0 else cost.swap_short
        while True:
            ob, hb, lb, sx = o[x], h[x], l[x], sp_raw[x] * mult
            if x > j and ((ex_ts and ts[x] >= ex_ts) or (max_bars and x - j >= max_bars)):
                px = ob - slip_m if side > 0 else ob + sx + slip_m
                reason = "time"
                break
            if side > 0:
                if ob <= stop:
                    px, reason = ob - slip_s, ("trail" if moved else "stop")
                    break
                if lb <= stop:
                    px, reason = stop - slip_s, ("trail" if moved else "stop")
                    break
                if target == target and hb >= target:
                    px, reason = (ob if ob > target else target), "target"
                    break
                worst = lb
            else:
                ask_o, ask_h, ask_l = ob + sx, hb + sx, lb + sx
                if ask_o >= stop:
                    px, reason = ask_o + slip_s, ("trail" if moved else "stop")
                    break
                if ask_h >= stop:
                    px, reason = stop + slip_s, ("trail" if moved else "stop")
                    break
                if target == target and ask_l <= target:
                    px, reason = (ask_o if ask_o < target else target), "target"
                    break
                worst = ask_h
            unreal = side * (worst - entry) * lots * contract - comm_rt * lots
            if equity + unreal < min_eq:
                min_eq = equity + unreal
            if trail == trail:
                if side > 0:
                    if hb > hh:
                        hh = hb
                    ns = hh - trail
                    if ns > stop:
                        stop, moved = ns, True
                else:
                    a = lb + sx
                    if a < ll:
                        ll = a
                    ns = ll + trail
                    if ns < stop:
                        stop, moved = ns, True
            if x + 1 >= n:
                px = c[x] - slip_m if side > 0 else c[x] + sx + slip_m
                reason = "end_of_data"
                break
            if flatten_gap_sec is not None and ts[x + 1] - ts[x] > flatten_gap_sec:
                px = c[x] - slip_m if side > 0 else c[x] + sx + slip_m
                reason = "gap_flat"
                break
            if sday[x + 1] != sday[x]:      # crossed the rollover: pay (or earn) one night of swap
                swap_oz += swap_rate * (cost.swap_wed_mult if m.dow_ny[x] == 2 else 1)
            x += 1

        pnl = side * (px - entry) * lots * contract - comm_rt * lots + swap_oz * lots * contract
        before = equity
        equity += pnl
        if equity < min_eq:
            min_eq = equity
        day_start.setdefault(sd, before)
        day_n[sd] = day_n.get(sd, 0) + 1
        day_pnl[sd] = day_pnl.get(sd, 0.0) + pnl
        rows.append({
            "entry_time": pd.Timestamp(ts[j], unit="s"), "exit_time": pd.Timestamp(ts[x], unit="s"),
            "side": side, "lots": lots, "entry": entry, "exit": px, "stop": stop0,
            "target": target, "risk_usd": planned_risk, "pnl": pnl,
            "r": pnl / planned_risk if planned_risk > 0 else 0.0,
            "pips": side * (px - entry) / acct.pip_size, "bars": x - j + 1,
            "reason": reason, "tag": int(sigs.tag[i]), "equity": equity, "signal_i": i,
            "swap": swap_oz * lots * contract,
        })
        cur = x

    if halted_at is None and acct.equity_floor > 0 and rows and equity <= acct.equity_floor + acct.halt_buffer:
        halted_at = rows[-1]["exit_time"]
    if halted_at is not None and not isinstance(halted_at, pd.Timestamp):
        halted_at = pd.Timestamp(halted_at, unit="s")

    cols = ["entry_time", "exit_time", "side", "lots", "entry", "exit", "stop", "target", "risk_usd",
            "pnl", "r", "pips", "bars", "reason", "tag", "equity", "signal_i", "swap"]
    trades = pd.DataFrame(rows, columns=cols)
    return BacktestResult(trades, dict(skips), equity, min_eq, halted_at, nsig, acct, cost)
