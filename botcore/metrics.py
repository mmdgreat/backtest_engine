"""Performance statistics. R-multiple = trade P&L / the dollars risked at the stop when the trade was sized."""
import numpy as np
import pandas as pd


def basic(t):
    if len(t) == 0:
        return {"n": 0, "win_rate": 0.0, "exp_r": 0.0, "profit_factor": 0.0, "total_r": 0.0,
                "pnl": 0.0, "avg_win_usd": 0.0, "avg_loss_usd": 0.0, "avg_pips": 0.0}
    r = t["r"].to_numpy(dtype=float)
    pnl = t["pnl"].to_numpy(dtype=float)
    gw, gl = r[r > 0].sum(), -r[r < 0].sum()
    return {
        "n": int(len(t)),
        "win_rate": float((r > 0).mean()),
        "exp_r": float(r.mean()),
        "profit_factor": float(gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0),
        "total_r": float(r.sum()),
        "pnl": float(pnl.sum()),
        "avg_win_usd": float(pnl[pnl > 0].mean()) if (pnl > 0).any() else 0.0,
        "avg_loss_usd": float(pnl[pnl < 0].mean()) if (pnl < 0).any() else 0.0,
        "avg_pips": float(t["pips"].mean()),
    }


def _max_streak(flags):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def bootstrap_mean_r(r, b=2000, seed=7):
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n < 10:
        return None
    if n > 4000:
        b = 800
    rng = np.random.default_rng(seed)
    means = r[rng.integers(0, n, size=(b, n))].mean(axis=1)
    return {"lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)),
            "p_le_zero": float((means <= 0).mean())}


def summarize(res, tag_names=None):
    acct = res.acct
    t = res.trades
    s = basic(t)
    s["initial_capital"] = acct.initial_capital
    s["final_equity"] = res.final_equity
    s["return_pct"] = 100.0 * (res.final_equity / acct.initial_capital - 1.0)
    s["min_equity"] = res.min_equity
    s["floor"] = acct.equity_floor
    s["floor_breached"] = bool(acct.equity_floor > 0 and res.min_equity < acct.equity_floor - 1e-9)
    s["halted_at"] = str(res.halted_at) if res.halted_at is not None else None
    s["signals"] = int(res.n_signals)
    s["skips"] = res.skips
    if len(t):
        eq = acct.initial_capital + t["pnl"].cumsum().to_numpy()
        eq = np.concatenate(([acct.initial_capital], eq))
        peak = np.maximum.accumulate(eq)
        dd = peak - eq
        s["max_dd_usd"] = float(dd.max())
        s["max_dd_pct"] = float((dd / peak).max() * 100.0)
        cr = np.cumsum(t["r"].to_numpy())
        cr = np.concatenate(([0.0], cr))
        s["max_dd_r"] = float((np.maximum.accumulate(cr) - cr).max())
        s["max_consec_losses"] = _max_streak((t["r"] <= 0).to_numpy())
        s["avg_bars"] = float(t["bars"].mean())
        span_days = max((t["entry_time"].iloc[-1] - t["entry_time"].iloc[0]).days, 1)
        s["trades_per_month"] = float(len(t) / (span_days / 30.44))
        s["bootstrap"] = bootstrap_mean_r(t["r"].to_numpy())
        s["long"] = basic(t[t["side"] > 0])
        s["short"] = basic(t[t["side"] < 0])
        yr = t["entry_time"].dt.year
        s["by_year"] = {int(y): basic(g) for y, g in t.groupby(yr)}
        names = tag_names or []
        s["by_tag"] = {(names[k] if k < len(names) else str(k)): basic(g) for k, g in t.groupby("tag")}
        s["by_exit"] = {k: int(v) for k, v in t["reason"].value_counts().items()}
    else:
        s.update({"max_dd_usd": 0.0, "max_dd_pct": 0.0, "max_dd_r": 0.0, "max_consec_losses": 0,
                  "avg_bars": 0.0, "trades_per_month": 0.0, "bootstrap": None, "long": basic(t),
                  "short": basic(t), "by_year": {}, "by_tag": {}, "by_exit": {}})
    return s
