"""Report writing: markdown summary, trades csv, equity chart."""
import json

import pandas as pd


def _f(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, float):
        if x == float("inf"):
            return "inf"
        return f"{x:.{nd}f}"
    return str(x)


def _row(label, b):
    return (f"| {label} | {b['n']} | {100 * b['win_rate']:.1f}% | {_f(b['exp_r'], 3)} | "
            f"{_f(b['profit_factor'])} | {_f(b['total_r'], 1)} | {_f(b['pnl'])} |")


HEAD = "| | trades | win rate | exp R | profit factor | total R | P&L $ |\n| --- | --- | --- | --- | --- | --- | --- |"


def markdown(title, mode, params, s, extra=""):
    L = [f"# {title} - {mode}", ""]
    L.append(f"Run settings: {mode}. Trades taken {s['n']}, signals {s['signals']}.")
    L.append("")
    L.append(f"Start ${_f(s['initial_capital'])} -> end ${_f(s['final_equity'])} "
             f"({_f(s['return_pct'], 1)}%). Lowest equity reached: ${_f(s['min_equity'])}"
             + (f" (floor ${_f(s['floor'])})" if s["floor"] else "") + ".")
    if s["floor_breached"]:
        L.append("**WARNING: equity went below the floor (gap or slippage beyond the planned stop).**")
    if s["halted_at"]:
        L.append(f"**Bot halted at {s['halted_at']}: equity reached the floor buffer.**")
    L += ["", "## Headline", "", HEAD, _row("all trades", s)]
    L += ["", f"Max drawdown: ${_f(s['max_dd_usd'])} ({_f(s['max_dd_pct'], 1)}%) / {_f(s['max_dd_r'], 1)} R. "
              f"Longest losing streak: {s['max_consec_losses']}. Average hold: {_f(s['avg_bars'], 1)} bars. "
              f"Trades per month: {_f(s['trades_per_month'], 1)}. Average result: {_f(s['avg_pips'])} pips per trade."]
    bs = s.get("bootstrap")
    if bs:
        L.append(f"Bootstrap 95% range for mean R per trade: {_f(bs['lo'], 3)} to {_f(bs['hi'], 3)} "
                 f"(chance the true mean is <= 0: {100 * bs['p_le_zero']:.1f}%).")
    L += ["", "## Split", "", HEAD, _row("long", s["long"]), _row("short", s["short"])]
    if s["by_year"]:
        L += ["", "## By year", "", HEAD] + [_row(str(y), b) for y, b in s["by_year"].items()]
    if len(s["by_tag"]) > 1:
        L += ["", "## By setup", "", HEAD] + [_row(k, b) for k, b in s["by_tag"].items()]
    if s["by_exit"]:
        L += ["", "## How trades ended", ""] + [f"- {k}: {v}" for k, v in s["by_exit"].items()]
    L += ["", "## Signals and skips", "", f"Signals generated: {s['signals']}. Trades taken: {s['n']}."]
    if s["skips"]:
        L += [f"- skipped, {k}: {v}" for k, v in sorted(s["skips"].items(), key=lambda kv: -kv[1])]
    L += ["", "## Parameters", "", "```json", json.dumps(params, indent=2, default=str), "```"]
    if extra:
        L += ["", extra]
    return "\n".join(L) + "\n"


def save_equity_png(trades, path, title, initial, floor=0.0):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    if len(trades) == 0:
        return False
    fig, ax = plt.subplots(figsize=(9, 4))
    eq = pd.concat([pd.Series([initial]), trades["equity"].reset_index(drop=True)], ignore_index=True)
    ax.plot(eq.index, eq.values, lw=1.4)
    if floor:
        ax.axhline(floor, color="red", ls="--", lw=1, label=f"floor ${floor:g}")
        ax.legend()
    ax.set_title(title)
    ax.set_xlabel("trade #")
    ax.set_ylabel("equity $")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return True


SKIP_LABELS = {
    "floor_no_room": "no room above the equity floor (account exhausted)",
    "halted": "bot halted (equity reached floor buffer)",
    "daily_loss_limit": "daily loss limit already reached",
    "max_trades_per_day": "max trades per day reached",
    "stale_signal": "signal expired before it could be filled",
    "spread_too_wide": "spread too wide at entry",
    "expired": "signal expired (entry window passed)",
    "stop_too_tight": "stop closer than minimum distance",
    "target_invalid": "target on the wrong side of entry",
    "stop_too_wide_for_risk": "stop too wide: 0.01 lot would risk more than allowed",
}


def risk_text(acct):
    base = "initial balance" if not acct.compounding else "current balance (never below initial)"
    return f"{100 * acct.risk_pct:g}% of {base} = ${acct.risk_pct * acct.initial_capital:,.2f} per trade" \
        if not acct.compounding else f"{100 * acct.risk_pct:g}% of {base}, capped by room above floor"


def usd(x, sign=False):
    return f"{'-' if x < 0 else ('+' if sign else '')}${abs(x):,.2f}"


def console_summary(name, title, data_desc, acct, cost, s):
    """Readable multi-line block for the terminal. Plain text, fixed-width columns."""
    n = s["n"]
    wins = int(round(s["win_rate"] * n))
    W = 24

    def line(k, v):
        return f"  {k:<{W}}{v}"

    out = ["", "=" * 74, f" {title}   [{name}]", "=" * 74, "", " SETUP"]
    out.append(line("Data", data_desc))
    out.append(line("Account type", "RESEARCH (virtual, judges the edge)" if acct.label == "research" else "REAL (the $100 account with floor)"))
    out.append(line("Initial balance", f"${acct.initial_capital:,.2f}"))
    out.append(line("Equity floor", f"${acct.equity_floor:,.2f}" if acct.equity_floor else "none"))
    out.append(line("Risk per trade", risk_text(acct)))
    out.append(line("Lot size limits", f"{acct.min_lot:g} to {acct.max_lot:g} lots"))
    out.append(line("Costs", f"spread from data and slippage, cost multiplier x{cost.cost_mult:g}"))
    out += ["", " TRADES"]
    out.append(line("Signals generated", f"{s['signals']:,}"))
    skipped = sum(s["skips"].values()) if s["skips"] else 0
    out.append(line("Signals skipped", f"{skipped:,}"))
    out.append(line("Trades taken", f"{n:,}"))
    if n:
        out.append(line("Wins / losses", f"{wins:,} / {n - wins:,}   (win rate {100 * s['win_rate']:.1f}%)"))
        out.append(line("Long / short", f"{s['long']['n']:,} / {s['short']['n']:,}"))
        out.append(line("Trades per month", f"{s['trades_per_month']:.1f}"))
        out.append(line("Average hold", f"{s['avg_bars']:.1f} bars (5 min each)"))
        out.append(line("Avg win / avg loss", f"{usd(s['avg_win_usd'])} / {usd(s['avg_loss_usd'])}"))
        out.append(line("Longest losing streak", f"{s['max_consec_losses']} trades"))
        out += ["", " RESULT"]
        out.append(line("Expectancy", f"{s['exp_r']:+.3f} R per trade   (R = amount risked on the trade)"))
        pf = s["profit_factor"]
        out.append(line("Profit factor", "inf" if pf == float("inf") else f"{pf:.2f}   (1.00 = break-even)"))
        out.append(line("Total", f"{s['total_r']:+.1f} R"))
        out.append(line("Net profit / loss", usd(s['pnl'], True)))
        bs = s.get("bootstrap")
        if bs:
            out.append(line("95% range (exp. R)", f"{bs['lo']:+.3f} to {bs['hi']:+.3f}   "
                                                 f"(chance true edge <= 0: {100 * bs['p_le_zero']:.0f}%)"))
        out += ["", " ACCOUNT"]
        out.append(line("Start equity", f"${s['initial_capital']:,.2f}"))
        out.append(line("End equity", f"${s['final_equity']:,.2f}   ({s['return_pct']:+.1f}%)"))
        out.append(line("Lowest equity", f"${s['min_equity']:,.2f}"))
        out.append(line("Max drawdown", f"${s['max_dd_usd']:,.2f}  ({s['max_dd_pct']:.1f}%)  /  {s['max_dd_r']:.1f} R"))
        if s["by_year"]:
            out += ["", " BY YEAR", f"  {'year':<6}{'trades':>8}{'win %':>8}{'exp R':>9}{'PF':>7}{'P&L $':>14}"]
            for y, b in s["by_year"].items():
                pf = "inf" if b["profit_factor"] == float("inf") else f"{b['profit_factor']:.2f}"
                out.append(f"  {y:<6}{b['n']:>8,}{100 * b['win_rate']:>7.1f}%{b['exp_r']:>+9.3f}{pf:>7}{b['pnl']:>14,.0f}")
        if s["by_exit"]:
            out += ["", " HOW TRADES ENDED"]
            out += [f"  {k:<22}{v:>7,}" for k, v in s["by_exit"].items()]
    else:
        out.append(line("Note", "no trades were taken"))
    if s["skips"]:
        out += ["", " SKIPPED SIGNALS (why)"]
        for k, v in sorted(s["skips"].items(), key=lambda kv: -kv[1]):
            out.append(f"  {v:>7,}  {SKIP_LABELS.get(k, k)}")
    warn = []
    if s["halted_at"]:
        warn.append(f"BOT HALTED at {s['halted_at']}: equity reached the floor buffer, later signals were not traded.")
    if s["floor_breached"]:
        warn.append("Equity went below the floor (gap or slippage beyond the planned stop).")
    if s["skips"].get("floor_no_room", 0):
        warn.append("The account ran out of room: the results cover only the period before that.")
    if warn:
        out += ["", " WARNINGS"] + [f"  ! {w}" for w in warn]
    out.append("")
    return "\n".join(out)
