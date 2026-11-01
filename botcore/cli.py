"""Shared command line used by every strategy's run.py.

    python run.py                      backtest with the real $100 / $70 account rules
    python run.py --research           same strategy on a virtual $1,000,000 account (judge the edge in R)
    python run.py --grid               run the strategy's small parameter grid (research mode)
    python run.py --walkforward        train/test walk-forward over that grid (research mode)
    python run.py --baseline 100       compare with 100 random-direction runs on the same entries
    python run.py --cost-mult 2        double spread and slippage (stress test)
    python run.py --set stop_atr=2.0   override any parameter for this run
"""
import argparse
import datetime as dt
import json
import os

import numpy as np
import pandas as pd

from . import account as acc
from . import report
from .data import load_market
from .engine import BacktestResult, run_backtest
from .metrics import basic, summarize
from .walkforward import grid_table, run_grid, walk_forward


def apply_overrides(params, sets):
    p = dict(params)
    for kv in sets:
        if "=" not in kv:
            raise SystemExit(f"--set expects KEY=VALUE, got {kv}")
        k, v = kv.split("=", 1)
        if k not in p:
            raise SystemExit(f"unknown parameter '{k}'. Valid: {sorted(p)}")
        old = p[k]
        if isinstance(old, bool):
            p[k] = v.lower() in ("1", "true", "yes", "y")
        elif isinstance(old, int):
            p[k] = int(v)
        elif isinstance(old, float):
            p[k] = float(v)
        elif isinstance(old, (list, tuple)):
            items = [x.strip() for x in v.split(",") if x.strip()]
            sample = old[0] if old else ""
            p[k] = [int(x) if isinstance(sample, int) and not isinstance(sample, bool) else
                    float(x) if isinstance(sample, float) else x for x in items]
        else:
            p[k] = v
    return p


def _pseudo_result(trades, acct, cost):
    final = acct.initial_capital + float(trades["pnl"].sum()) if len(trades) else acct.initial_capital
    return BacktestResult(trades, {}, final, final, None, len(trades), acct, cost)


def main(P, S, argv=None):
    ap = argparse.ArgumentParser(description=f"{P.TITLE} bot", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--source", choices=["mongo", "csv"], default="mongo")
    ap.add_argument("--csv", help="candles CSV (time,open,high,low,close,tick_volume,spread)")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--research", action="store_true")
    ap.add_argument("--capital", type=float)
    ap.add_argument("--floor", type=float)
    ap.add_argument("--risk-pct", type=float)
    ap.add_argument("--cost-mult", type=float, default=1.0)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--walkforward", action="store_true")
    ap.add_argument("--train-months", type=int, default=6)
    ap.add_argument("--test-months", type=int, default=2)
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--baseline", type=int, default=0, metavar="N")
    ap.add_argument("--out")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args(argv)

    m = load_market(args.source, args.csv, start=args.start, end=args.end)
    print(f"[{P.NAME}] data: {m.describe()}")
    if m.tf_sec != 300:
        print(f"WARNING: base timeframe is {m.tf_sec // 60} min; the strategies are written for M5 data.")

    params = apply_overrides(P.PARAMS, args.set)
    base_acct = acc.RESEARCH if args.research else acc.REAL
    acct = acc.with_overrides(base_acct, args.capital, args.floor, args.risk_pct)
    cost = acc.CostModel(cost_mult=args.cost_mult)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.dirname(os.path.abspath(P.__file__))
    out = args.out or os.path.join(folder, "results", stamp)
    os.makedirs(out, exist_ok=True)
    kw = dict(max_trades_per_day=P.MAX_TRADES_PER_DAY, flatten_gap_sec=P.FLATTEN_GAP_SEC,
              max_entry_gap_sec=getattr(P, "MAX_ENTRY_GAP_SEC", None))

    # ---- main backtest ---------------------------------------------------------------------
    sigs = S.build_signals(m, params)
    res = run_backtest(m, sigs, acct, cost, **kw)
    s = summarize(res, sigs.tags)
    mode = f"{acct.label} account (${acct.initial_capital:,.0f}, floor ${acct.equity_floor:,.0f}, cost x{cost.cost_mult:g})"
    extra = []

    # ---- optional: random-direction baseline ----------------------------------------------
    if args.baseline > 0:
        exps = []
        for k in range(args.baseline):
            rr = run_backtest(m, sigs, acct, cost, rng=np.random.default_rng(1000 + k), **kw)
            exps.append(basic(rr.trades)["exp_r"])
        exps = np.array(exps)
        p = float((exps >= s["exp_r"]).mean())
        txt = (f"## Random-direction baseline\n\nSame entry times and same stop/target distances, but a coin flip for "
               f"direction, {args.baseline} runs. Random mean R per trade: median {np.median(exps):.3f} "
               f"(5th-95th percentile {np.percentile(exps, 5):.3f} to {np.percentile(exps, 95):.3f}). "
               f"This strategy: {s['exp_r']:.3f}. Share of random runs that did as well or better: {100 * p:.1f}%.")
        extra.append(txt)
        print(f"[{P.NAME}] baseline: strategy {s['exp_r']:.3f} R vs random median {np.median(exps):.3f} R "
              f"(random did as well in {100 * p:.1f}% of {args.baseline} runs)")

    # ---- optional: grid and walk-forward (always research mode) ---------------------------
    if args.grid or args.walkforward:
        racct = acc.with_overrides(acc.RESEARCH, args.capital, args.floor, args.risk_pct)
        runs = run_grid(m, S.build_signals, params, P.GRID, racct, cost, **kw)
        gt = grid_table(runs)
        gt.to_csv(os.path.join(out, "grid.csv"), index=False)
        print(f"[{P.NAME}] grid ({len(runs)} combinations, research mode), best first:")
        print(gt.head(12).to_string(index=False))
        extra.append(f"## Parameter grid ({len(runs)} combinations tried)\n\nSorted by mean R per trade. "
                     "A real edge shows up as a cluster of neighbouring settings that all work, not one lucky row.\n\n"
                     "```\n" + gt.to_string(index=False) + "\n```")
        pos = int((gt["exp_r"] > 0).sum())
        print(f"[{P.NAME}] {pos} of {len(gt)} combinations had positive expectancy over the full period")
        if args.walkforward:
            wf, oos = walk_forward(runs, m.when(0), m.when(m.n - 1), args.train_months, args.test_months, args.min_trades)
            wf.to_csv(os.path.join(out, "walkforward_windows.csv"), index=False)
            print(wf.to_string(index=False))
            if len(oos):
                oos.to_csv(os.path.join(out, "walkforward_oos_trades.csv"), index=False)
                so = summarize(_pseudo_result(oos, racct, cost), sigs.tags)
                json.dump(so, open(os.path.join(out, "walkforward_oos_summary.json"), "w"), indent=2, default=str)
                extra.append("## Walk-forward (out-of-sample only)\n\nWindows: train "
                             f"{args.train_months} months, test {args.test_months} months, at least {args.min_trades} train trades, "
                             "sit out when the best train expectancy is not positive.\n\n"
                             f"{report.HEAD}\n{report._row('out-of-sample', so)}\n\n```\n{wf.to_string(index=False)}\n```")
                print(f"[{P.NAME}] OUT-OF-SAMPLE: {so['n']} trades, {so['exp_r']:.3f} R/trade, "
                      f"PF {so['profit_factor']:.2f}, total {so['total_r']:.1f} R")
            else:
                extra.append("## Walk-forward\n\nNo window produced a tradable choice: nothing qualified out of sample.")
                print(f"[{P.NAME}] walk-forward: no tradable windows")

    # ---- outputs ----------------------------------------------------------------------------
    md = report.markdown(P.TITLE, mode, params, s, "\n\n".join(extra))
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write(md)
    res.trades.to_csv(os.path.join(out, "trades.csv"), index=False)
    json.dump(s, open(os.path.join(out, "summary.json"), "w"), indent=2, default=str)
    if not args.no_plot:
        report.save_equity_png(res.trades, os.path.join(out, "equity.png"), f"{P.TITLE} - {acct.label}",
                               acct.initial_capital, acct.equity_floor)
    print(report.console_summary(P.NAME, P.TITLE, m.describe(), acct, cost, s))
    print(f"  Files saved in: {out}")
    print(f"      report.md (full report)   trades.csv (every trade)   summary.json   equity.png\n")
    return res, s
