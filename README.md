# XAUUSD strategy bots

Six independent backtest bots, one folder each, sharing one frozen simulation engine.
**To install and test everything step by step, follow `DEPLOY_GUIDE.md`.**
`STRATEGY_RULES.md` lists the rules every bot follows and the exact rules of each strategy.
These are backtest bots: they never place orders.

```
DEPLOY_GUIDE.md          install, load data, test all six strategies, decide (start here)
STRATEGY_RULES.md        the one rules document
botcore/                 shared engine (data, sessions, indicators, fills, account rules, metrics, CLI)
s1_orb/                  Opening Range Breakout
s2_liquidity_sweep/      Liquidity Sweep + Reversal
s3_trend_pullback/       Trend Pullback
s4_donchian_h4/          Donchian H4 Breakout
s5_mean_reversion/       Mean Reversion (Asian session)
s6_squeeze_breakout/     Volatility Squeeze / NR7 Breakout
    params.py            settings you tune
    strategy.py          the rules in code
    run.py               the command line for this bot
    tuning_log.md        your notes, one row per run
    results/             created on the first run: one sub-folder per run
data_tools/              Phase 1: MT5 check, sync candles to MongoDB, data quality check
tests/                   engine tests and strategy look-ahead tests
tools/                   synthetic data generator (for offline code checks only)
```

## Setup (PowerShell, Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install pymongo pandas numpy matplotlib MetaTrader5
python tests\test_engine.py
python tests\test_strategies.py
python -m botcore.check_clock
```

Both test files must pass. `check_clock` confirms your broker's server time is New York + 7 hours
(if not, change `SERVER_MINUS_NY_HOURS` in `botcore/settings.py`).
MongoDB must be running with candles in `trading.candles` (see `data_tools/sync_candles.py`).

## Running one bot

```
cd s1_orb
python run.py                               real account: $100 start, $70 floor
python run.py --research                    virtual $1,000,000, fixed $1,000 risk, judge the edge in R
python run.py --research --baseline 100     compare with 100 random-direction runs
python run.py --research --cost-mult 2      double spread and slippage
python run.py --research --grid             run the small parameter grid
python run.py --research --grid --walkforward   out-of-sample test (the result that counts)
python run.py --set rr=3 --set atr_mult=1.5     override settings for one run
python run.py --start 2025-01-01 --end 2026-01-01
python run.py --source csv --csv candles.csv    use a CSV instead of MongoDB
```

Add `--no-plot` to skip the equity chart. Each run writes `report.md`, `trades.csv`, `summary.json`
and `equity.png` into `results/<timestamp>/`.

## Testing the code without real data

```
python tools\make_synthetic_data.py --out synth.csv --days 700 --seed 1
cd s1_orb
python run.py --source csv --csv ..\synth.csv --research
```

The default synthetic data is a pure random walk, so strategies should NOT profit on it. `--trend 0.3` plants
momentum so a trend follower should profit (a positive control). Neither says anything about real gold.
