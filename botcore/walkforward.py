"""Walk-forward evaluation.

Every combination in the strategy's small GRID is simulated ONCE over the whole data in research mode
(fixed-risk, no floor). Signals are causal, so a trade's outcome does not depend on which window it is
later assigned to; the only approximation is a trade that straddles a window boundary.

For each window the best combination on the TRAIN period is chosen, then ONLY its trades from the
following TEST period are kept. The stitched test trades are the honest, out-of-sample result.
A window sits out when no combination has enough trades or a positive train expectancy."""
import itertools

import numpy as np
import pandas as pd

from .engine import run_backtest
from .metrics import basic


def grid_combos(grid):
    keys = list(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*[grid[k] for k in keys])]


def run_grid(m, build_signals, base_params, grid, acct, cost, max_trades_per_day, flatten_gap_sec,
             max_entry_gap_sec=None):
    out = []
    for combo in grid_combos(grid):
        p = {**base_params, **combo}
        sigs = build_signals(m, p)
        res = run_backtest(m, sigs, acct, cost, max_trades_per_day, flatten_gap_sec,
                           max_entry_gap_sec=max_entry_gap_sec)
        out.append({"params": combo, "trades": res.trades, "signals": sigs.count()})
    return out


def grid_table(runs):
    rows = []
    for r in runs:
        b = basic(r["trades"])
        rows.append({**r["params"], "trades": b["n"], "win_rate": round(b["win_rate"], 3),
                     "exp_r": round(b["exp_r"], 3), "profit_factor": round(b["profit_factor"], 2),
                     "total_r": round(b["total_r"], 1)})
    return pd.DataFrame(rows).sort_values("exp_r", ascending=False).reset_index(drop=True)


def walk_forward(runs, first, last, train_months=6, test_months=2, min_trades=30):
    """runs: output of run_grid. first/last: pandas Timestamps bounding the data."""
    windows, picked = [], []
    start = pd.Timestamp(first).normalize()
    last = pd.Timestamp(last)
    while True:
        tr_end = start + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if tr_end >= last:
            break
        best, best_score = None, -1e9
        for r in runs:
            t = r["trades"]
            tt = t[(t["entry_time"] >= start) & (t["entry_time"] < tr_end)]
            b = basic(tt)
            if b["n"] >= min_trades and b["exp_r"] > 0 and b["exp_r"] > best_score:
                best, best_score = r, b["exp_r"]
        row = {"train_start": start.date(), "train_end": tr_end.date(), "test_end": min(te_end, last).date()}
        if best is None:
            row.update({"chosen": "sit out", "train_exp_r": None, "test_n": 0, "test_exp_r": None})
        else:
            t = best["trades"]
            te = t[(t["entry_time"] >= tr_end) & (t["entry_time"] < te_end)]
            picked.append(te)
            bt = basic(te)
            row.update({"chosen": str(best["params"]), "train_exp_r": round(best_score, 3),
                        "test_n": bt["n"], "test_exp_r": round(bt["exp_r"], 3) if bt["n"] else None})
        windows.append(row)
        start = start + pd.DateOffset(months=test_months)
    oos = pd.concat(picked, ignore_index=True) if picked else pd.DataFrame()
    return pd.DataFrame(windows), oos
