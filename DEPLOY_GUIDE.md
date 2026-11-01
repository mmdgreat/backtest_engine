# Deploy and Test Guide - six XAUUSD strategy bots

Follow the steps in order. Each step ends with a **Check** that tells you it worked before you move on.
The rules of each strategy are in `STRATEGY_RULES.md`; this file is only about installing, loading data and testing.

> **What "deploy" means here.** These six bots are **backtest bots**. They never place orders and never log in to
> MT5. Only the small tools in `data_tools/` talk to MT5, and only to read candles. Following this guide installs
> the test lab on your laptop, loads gold history into MongoDB and runs every strategy through the same tests.
> Placing demo or live orders is a later phase, and only for strategies that pass these tests (Step 9).

## At a glance

| Step | What | Roughly how long |
| --- | --- | --- |
| 1 | Check what you need | 5 min |
| 2 | Install | 10 min |
| 3 | Verify the code (no data needed) | 2 min |
| 4 | Load and check your data | 20 min plus download time |
| 5 | Quick run of all six bots | 10-20 min |
| 6 | Full test of each strategy | see the note in Step 6 |
| 7 | Record results and decide | 15 min per strategy |
| 8 | Tune, one change at a time | ongoing |
| 9 | What comes next | - |

---

## Step 1 - Check what you need

- Windows laptop with **Python 3.10 or newer** (`python --version`; the code was tested here on Python 3.13).
- **MT5 (Vantage) open and logged in to a DEMO account.** Never use a real-money account with anything in this folder.
- **MongoDB running** on `localhost:27017` with your candles in database `trading`, collection `candles`
  (documents with `time`, `symbol` = "XAUUSD", `tf` = "M5", `open`, `high`, `low`, `close`, `tick_volume`, `spread`).
  MongoDB Compass is handy for looking at the data but is not required.
- The file `xauusd-bots.zip`.

## Step 2 - Install

Open **PowerShell** and run:

```
Expand-Archive "$env:USERPROFILE\Downloads\xauusd-bots.zip" -DestinationPath C:\
cd C:\xauusd-bots
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pymongo pandas numpy matplotlib MetaTrader5
```

If PowerShell refuses to run `Activate.ps1` ("running scripts is disabled"), run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.
Run every later command from `C:\xauusd-bots` with the virtual environment active (you will see `(.venv)` in the prompt),
unless the step says to go into a different folder.

**Check:** `python -c "import pandas, numpy, pymongo, matplotlib, MetaTrader5; print('imports ok')"` prints `imports ok`.

## Step 3 - Verify the code

```
python tests\test_engine.py
python tests\test_strategies.py
```

**Check:** the first ends with `18 engine tests passed`, the second with `7 strategy checks passed`.
The first proves the fill simulator follows the rules (spread, slippage, stop-first, the $70 floor). The second proves
no strategy can see the future. **If either fails, stop and send me the output.**

## Step 4 - Load and check your data

### 4.1 Confirm the MT5 connection and that the account is DEMO

```
cd data_tools
python mt5_check.py
```

**Check:** the output says `type: DEMO`, shows symbol details (contract size, which is normally 100 for gold, minimum lot, spread) and three recent M5 bars.
If it says anything other than DEMO, stop. If MT5 cannot be reached, see Troubleshooting.

### 4.2 Make the symbol name match everywhere

Your broker may call gold `XAUUSD`, `XAUUSDm`, `GOLD` and so on. The name in `data_tools\config.py` (`SYMBOL`) must match
MT5's Market Watch, **and** `SYMBOL` in `botcore\settings.py` must match the `symbol` field stored in MongoDB.
Your existing documents say `"XAUUSD"`, so if Vantage uses exactly that, leave both files alone.
If your MongoDB is not on `localhost:27017`, set the address once per PowerShell session: `$env:MONGO_URI = "mongodb://host:port"`.

### 4.3 Load more history, then bring it up to date

You have about 19 months (from 2024-11-15). More history makes every test more trustworthy, so load as much as Vantage
keeps. In MT5 first set **Tools > Options > Charts > Max bars in chart = Unlimited** and restart MT5, then:

```
python sync_candles.py --backfill --since 2021-01-01
python sync_candles.py
```

- `--backfill` loads the **older** bars from the date you give up to your oldest stored bar. (Plain `--since` only applies
  to a timeframe with no data yet, so it would not load older history on its own.)
- The second command adds everything newer than your newest bar. It is safe to run at any time, as often as you like.
- How far back you can go depends on Vantage. If the oldest bars come out later than you asked for, that is all the broker has.
- It also saves the broker's contract specs (lot size, swap, stops level) into a `symbol_specs` collection.

**Check:** both commands finish with `saved broker symbol specs`.

### 4.4 Check the data quality

```
python check_data.py
```

**Check:** the output shows how many rows and the first and last dates, and these should all be fine:

| Line | You want to see |
| --- | --- |
| `duplicate timestamps` | 0 (if not, run `python check_data.py --drop-duplicates`, then `sync_candles.py` again) |
| `bars with impossible OHLC` | 0 |
| `unexpected gaps` | none, or a few around holidays (Christmas, New Year). Many gaps mean missing data: run `sync_candles.py` again |
| `spread (points)` | sensible numbers (gold is usually 10-40 points on M5; zero-spread bars are suspicious) |

Then go back to the main folder: `cd ..`

### 4.5 Confirm the broker clock

All session logic (London open, New York open, Asian range) assumes the broker's server time is **New York + 7 hours** all year.

```
python -m botcore.check_clock
```

**Check:** the last line starts with `OK:`. That means the weekend and daily reopenings sit at the same server time (01:00) in winter and
summer, which is 18:00 New York with server = NY + 7h. A handful of isolated odd gaps (data holes, halts) are listed under
"Isolated odd gaps" and are ignored; the verdict looks at the time that 95% or more of the reopenings share.
If it says `CHECK:`, read the reason: if the time moves between seasons, or is constant at a different hour, do not trust any
session-based result (S1, S2, S3, S5, S6) until the offset is fixed. The message says what to change. Send me the full output.

### 4.6 How much data is enough?

| History | What you can trust |
| --- | --- |
| Under 12 months | Smoke tests only. Walk-forward will not work |
| 1.5-2 years (what you have now) | First look at S1, S2, S3, S5, S6. S4 and S6 will have few trades |
| 3-5 years | Needed to judge S4 and to trust any pass/fail verdict |

---

## Step 5 - Quick run of all six bots (smoke test on your real data)

This only checks that every bot runs on your data and produces trades. It says nothing about whether a strategy works.

```
foreach ($s in "s1_orb","s2_liquidity_sweep","s3_trend_pullback","s4_donchian_h4","s5_mean_reversion","s6_squeeze_breakout") {
    Push-Location $s
    python run.py --research --no-plot --out results\0_smoke
    Pop-Location
}
```

**Check:** each bot prints a line like `[s1_orb] signals 950 | trades 939 | win 35.5% | exp -0.035 R | PF 0.95 ...` and `results saved in ...`.
On 700 days of synthetic data, S1, S2, S3 and S5 each gave several hundred signals or more, and S4 and S6 about 100. Real gold
will differ, but **a bot with 0 signals means a data or clock problem**: see Troubleshooting before going on.

## Step 6 - Full test of each strategy

Every strategy gets the same five tests. Run them in **research mode** (a virtual $1,000,000 with a fixed $1,000 risk per trade, no floor and no daily-loss stop, so the account can never run out and every signal in the history is tested), because the
real $100 account's 0.01-lot minimum distorts the result. Research mode answers "does the idea have an edge?"; the last test answers
"can the $100 / $70 account actually trade it?".

| # | Test | Command (inside the strategy folder) | What it answers |
| --- | --- | --- | --- |
| 1 | Baseline | `python run.py --research --out results\1_baseline` | The headline numbers on the whole history |
| 2 | Random baseline | `python run.py --research --baseline 100 --out results\2_random_baseline` | Same entries and stops, direction chosen by coin flip, 100 times. Does the strategy beat luck? |
| 3 | Cost stress | `python run.py --research --cost-mult 2 --out results\3_cost_x2` | Spread and slippage doubled. Does it survive worse costs? |
| 4 | Grid + walk-forward | `python run.py --research --grid --walkforward --out results\4_grid_walkforward` | Tries the small parameter grid, then tests the best setting on data it never saw. **The result that counts** |
| 5 | Real account | `python run.py --out results\5_real_account` | $100 start, $70 floor, 0.01 lot minimum, 5% risk |

To run all five for every strategy, paste this function once into PowerShell (from `C:\xauusd-bots`), then the seven calls below it:

```
function Test-Strategy {
    param([string]$Folder, [string]$Prefix = "", [string[]]$Set = @(), [string[]]$Wf = @())
    $setArgs = @()
    foreach ($kv in $Set) { $setArgs += "--set"; $setArgs += $kv }
    Push-Location $Folder
    python run.py --research @setArgs --out "results\${Prefix}1_baseline"
    python run.py --research --baseline 100 @setArgs --out "results\${Prefix}2_random_baseline"
    python run.py --research --cost-mult 2 @setArgs --out "results\${Prefix}3_cost_x2"
    python run.py --research --grid --walkforward @Wf @setArgs --out "results\${Prefix}4_grid_walkforward"
    python run.py @setArgs --out "results\${Prefix}5_real_account"
    Pop-Location
}

Test-Strategy s1_orb
Test-Strategy s2_liquidity_sweep
Test-Strategy s3_trend_pullback
Test-Strategy s4_donchian_h4 -Wf "--train-months","12","--test-months","4","--min-trades","20"
Test-Strategy s5_mean_reversion
Test-Strategy s6_squeeze_breakout
Test-Strategy s6_squeeze_breakout -Prefix "nr7_" -Set "mode=nr7"
```

Notes on those calls:

- **S4** trades rarely (about 25-35 times a year), so it needs longer walk-forward windows and a lower trade minimum, as shown. Use 3+ years of data.
- **S6** has two modes and each is tested separately: the squeeze (default) and `mode=nr7` (results go to `results\nr7_...`). In NR7 mode the grid only varies `rr`, because the other grid settings belong to the squeeze mode.
- If a bot's walk-forward shows **every window as `sit out`**, either no setting had a positive result in training (a legitimate failure) or it had fewer than 30 training trades. For the second case add `-Wf "--min-trades","15"` or longer windows (`"--train-months","12","--test-months","4"`) and run Test 4 again by hand.
- **Time.** On 700 days of synthetic data each bot's whole protocol took 3 to 18 seconds on the machine I used. Your real data will be larger and your laptop is different, so expect minutes per strategy rather than seconds. I have not timed it on your machine. Use `--start` and `--end` to shorten experiments.

### How to read the results

Each run writes a folder under the bot's `results\` containing `report.md` (open this), `summary.json`, `trades.csv`, `equity.png`,
and for Test 4 also `grid.csv`, `walkforward_windows.csv` and `walkforward_oos_trades.csv`.

In `report.md`, look at these in order:

1. **Headline**: trades, win rate, **exp R** (average profit per trade in units of risk; positive is good), **profit factor** (total won divided by total lost; above 1 is good).
2. **The bootstrap line**: "95% range for mean R per trade" and "chance the true mean is <= 0". If the range straddles zero widely, the result cannot be told apart from luck.
3. **Split** (long vs short) and **By year**: a real edge usually shows in both directions and in more than one year. One lucky year or direction is a warning.
4. **By setup**: which session, pool or direction produces the result. Avoid trusting a strategy that only works through one narrow slice.
5. **How trades ended** and **Signals and skips**: how many ended on target, stop or time, and why signals were not traded.
6. For Test 2, the sentence "**Share of random runs that did as well or better**". You want this at or below 5%.
7. For Test 4, the console line `OUT-OF-SAMPLE: ...` (the report repeats the figures in its walk-forward section) gives the out-of-sample trades, average R and profit factor. `walkforward_windows.csv` has one row per window: count how many rows have a positive `test_exp_r`. `sit out` means no setting qualified in training for that window (its best training result was not positive, or it had too few trades).

### Pass bar

A strategy passes only if **all** of these hold on the out-of-sample (Test 4) result and the other tests:

| Check | Pass |
| --- | --- |
| Out-of-sample expectancy | above **+0.10 R** per trade after costs |
| Out-of-sample profit factor | above **1.2** |
| Out-of-sample trade count | at least **200** (S4 and S6: at least **60**, they trade rarely) |
| Walk-forward windows | profitable in **most** of the windows that traded |
| Cost stress (Test 3) | expectancy still **above 0** at doubled costs |
| Random baseline (Test 2) | random runs did as well in **5% or fewer** of the runs |
| Parameter grid | a **cluster** of neighbouring settings works, not one lucky row |

Verdicts: **PASS** (all of the above), **PROMISING** (positive and consistent but too few trades: get more data and rerun),
**DROP** (fails out-of-sample, cost stress or the random baseline). **Never pass a strategy on its in-sample numbers.**
A good Test 1 or a good-looking grid on its own proved nothing in my synthetic tests: on a pure random walk S4's grid showed 11 of 12
settings positive.

### Test 5: the real $100 account

Read it separately. Typical outcomes, and they are not bugs:

- `stop_too_wide_for_risk` skips: the stop is wider than the ~$4.90 the account can risk at 0.01 lot. S4 will skip almost everything.
- `halted`: equity reached $71 (floor $70 plus a $1 buffer) and the bot stopped for good. With only $30 of room, about six full stop-outs end the run.
- `floor_no_room`: the remaining room above the floor was too small for the next trade.

Record the end equity, minimum equity and how many signals were skipped. A strategy can pass Test 4 and still be untradable on this account;
that is a decision about account size or risk, not about the strategy.

## Step 7 - Record the results and decide

1. In each bot's `tuning_log.md`, write one row for the baseline run (date, command, trades, exp R, PF, out-of-sample exp R, verdict).
2. Fill one comparison table for all six (copy this into a note or spreadsheet):

| Strategy | Trades | Exp R | PF | Random baseline: % as good | Cost x2 exp R | OOS trades | OOS exp R | OOS PF | Windows profitable | Real account: end equity / halted? | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 ORB | | | | | | | | | | | |
| S2 Sweep | | | | | | | | | | | |
| S3 Pullback | | | | | | | | | | | |
| S4 Donchian | | | | | | | | | | | |
| S5 Mean rev. | | | | | | | | | | | |
| S6 Squeeze | | | | | | | | | | | |
| S6 NR7 | | | | | | | | | | | |

3. Drop every DROP. Keep PASS and PROMISING. Expect that some, perhaps most, will fail; that is the test doing its job.

---

## Step 8 - Tune, one change at a time

Only tune a strategy that is PASS or PROMISING. The rule that protects you from fooling yourself: **keep a hold-out period you never tune on.**

1. Pick a split date, for example the last 6 months. Tune on everything before it, and look at the hold-out only at the very end:

```
python run.py --research --end 2026-04-01 --out results\tune_a
python run.py --research --start 2026-04-01 --out results\holdout
```

(Replace the date with your own split. `--start` and `--end` take `YYYY-MM-DD`; `--end` is exclusive.)

2. Change **one** setting per run, either by editing that bot's `params.py`, or for a single run with `--set`:

```
python run.py --research --end 2026-04-01 --set rr=3 --out results\tune_b
python run.py --research --end 2026-04-01 --set atr_mult=1.5 --set rr=3 --out results\tune_c
```

   `--set` lists the valid names if you mistype one. Settings and their meanings are in `STRATEGY_RULES.md` and at the top of each `params.py`.
3. After each run add a row to that bot's `tuning_log.md`: what you changed (old to new), the command, trades, exp R, PF, the walk-forward result, and your verdict.
4. Judge every change on the **walk-forward out-of-sample** result, never on the in-sample numbers alone, and prefer changes that improve a neighbourhood of settings over a single peak.
5. When you are done, run the hold-out **once**. If it disagrees badly with your tuning period, the tuning overfitted; go back to the untuned defaults rather than tuning further.
6. If you change a default in `params.py`, update the matching table in `STRATEGY_RULES.md` so the document stays true.

## Step 9 - What comes next

- **Passing strategies** move on to a **forward test on the MT5 demo account**, which needs an execution layer that does not exist yet:
  order placement, a hard-coded risk engine (the $70 floor, daily loss limit, mandatory stops, kill switch), reconciliation and logging.
  Say the word and I will build it for the strategies that pass.
- **Before any demo trading**, add a **news blackout** (NFP, CPI, FOMC). The backtest does not avoid scheduled news and live gold does not forgive it.
- **Decide the account question.** If a strategy passes in research mode but is untradable on $100 / $70 (S4 almost certainly), the choices are a
  larger account, a smaller stop, or dropping it. That is your call, not a code fix.
- Demo fills are kinder than live fills. A strategy should run on demo for weeks, in different market conditions, before real money is considered. This is a technical process, not financial advice.

---

## Appendix A - Command cheat sheet

Run inside a strategy folder unless noted. Add `--no-plot` to skip the equity chart.

| Task | Command |
| --- | --- |
| Backtest on your $100 / $70 account | `python run.py` |
| Backtest in research mode (judge the edge) | `python run.py --research` |
| Random-direction comparison | `python run.py --research --baseline 100` |
| Double the costs | `python run.py --research --cost-mult 2` |
| Parameter grid | `python run.py --research --grid` |
| Grid + out-of-sample test | `python run.py --research --grid --walkforward` |
| Longer walk-forward windows | `... --walkforward --train-months 12 --test-months 4 --min-trades 20` |
| Change a setting for one run | `python run.py --set rr=3 --set atr_mult=1.5` |
| Limit the dates | `python run.py --start 2025-01-01 --end 2026-01-01` |
| Use a CSV instead of MongoDB | `python run.py --source csv --csv candles.csv` |
| Choose the results folder | `python run.py --out results\my_run` |
| All options | `python run.py --help` |
| Squeeze bot in NR7 mode | `python run.py --set mode=nr7` |
| Code tests (from `C:\xauusd-bots`) | `python tests\test_engine.py` and `python tests\test_strategies.py` |
| Clock check (from `C:\xauusd-bots`) | `python -m botcore.check_clock` |
| MT5 check / sync / data check (from `data_tools`) | `python mt5_check.py` / `python sync_candles.py` / `python check_data.py` |
| Load older history (from `data_tools`) | `python sync_candles.py --backfill --since 2021-01-01` |

## Appendix B - Troubleshooting

| What you see | Meaning and fix |
| --- | --- |
| `No XAUUSD M5 candles found in trading.candles` | MongoDB has no matching documents. Check that MongoDB is running, that the database and collection are `trading` and `candles`, and that documents have `symbol` = "XAUUSD" and `tf` = "M5" exactly. If your symbol differs, set `SYMBOL` in `botcore\settings.py` |
| `ServerSelectionTimeoutError` (after about 5 seconds) | Cannot reach MongoDB. Start the MongoDB service, or set `$env:MONGO_URI` to the right address |
| `MT5 initialize failed` | MT5 is closed, not logged in, or the path is wrong. Open MT5 and log in to the demo account, and check `MT5_TERMINAL_PATH` in `data_tools\config.py` |
| `Symbol XAUUSD not found at this broker` | Use the exact name from MT5's Market Watch (for example `XAUUSDm` or `GOLD`) in `data_tools\config.py`, and keep stored data and `botcore\settings.py` consistent with it |
| `Could not create the unique index` | Duplicate candles exist. Run `python check_data.py --drop-duplicates` in `data_tools`, then sync again |
| `ModuleNotFoundError` | The virtual environment is not active, or a package is missing. Run `.venv\Scripts\Activate.ps1`, then the `pip install` line from Step 2. Missing only `matplotlib`: install it, or add `--no-plot` |
| `WARNING: base timeframe is N min` | The loaded candles are not M5. The strategies are written for M5 data |
| `not enough candles` | Fewer than 100 bars were loaded. Check the `--start` / `--end` dates |
| `unknown parameter 'x'. Valid: [...]` | A `--set` name is misspelled. The message lists the valid names |
| `check_clock` ends with `CHECK:` | The broker clock does not follow New York + 7h. Do not trust session-based results; send me the full output |
| A bot shows 0 signals | Usually a data or clock problem: check Step 4.4 and 4.5, and that the date range covers London and New York hours |
| Real-account run is `halted` or skips most signals | Expected with $30 of room (see Test 5). Judge the idea in research mode |
| Every walk-forward window is `sit out` | Either nothing was profitable in training (a real result) or too few trades per window. Try `--min-trades 15` and longer windows |
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once |

**Skip reasons** shown in the `skipped:` line of every run:

| Reason | Meaning |
| --- | --- |
| `halted` | Equity reached floor + $1; the bot stopped for good |
| `floor_no_room` | Not enough room above the $70 floor to risk a minimum trade |
| `stop_too_wide_for_risk` | The stop is wider than the risk budget allows at 0.01 lot |
| `stop_too_tight` | The stop is closer than 0.50 to the fill price |
| `spread_too_wide` | The spread on the entry bar exceeded the limit |
| `max_trades_per_day` / `daily_loss_limit` | The daily trade cap or the 10% daily loss limit was reached |
| `stale_signal` / `expired` | The next bar was too late (a market break or weekend) or the trade window had already closed |
| `target_invalid` | The target was no longer on the profit side after costs |

## Appendix C - Where everything lives

```
C:\xauusd-bots\
  DEPLOY_GUIDE.md        this guide
  STRATEGY_RULES.md      the rules of every strategy
  README.md              short overview
  botcore\               shared engine (do not edit unless you mean to change the rules for all six bots)
  data_tools\            MT5 check, candle sync, data quality check
  tests\                 code tests
  tools\                 synthetic-data generator (offline code checks only)
  s1_orb\ ... s6_squeeze_breakout\
      params.py          the settings you tune
      strategy.py        the rules in code
      run.py             the command line for this bot
      tuning_log.md      your notes
      results\<name>\    report.md, trades.csv, summary.json, equity.png, grid.csv, walkforward_*.csv
```

## Appendix D - Load M1 candles (needed before any scalping test)

The six bots use M5. A scalper needs M1, and your broker may keep less M1 history than M5. Do this once.

1. **Let MT5 hold the history.** In MT5: Tools > Options > Charts > set *Max bars in chart* to **Unlimited** and press OK.
   Open an XAUUSD **M1** chart and press the **Home** key a few times (or hold it) so the terminal downloads older bars.
   Keep MT5 open and logged in to your Vantage demo account.
2. **Load it into MongoDB** (about 1.7 million bars for five years; it can take several minutes):

```
cd data_tools
python sync_candles.py --tf M1 --since 2021-01-04
```

   It prints progress, then `now stored: ... bars, oldest ...`. If it prints a WARNING that the oldest bar is later than
   2021-01-04, the broker simply does not hold that much M1 history: that is fine, scalp tests will then cover the years
   available. Running the same command again later adds only newer bars.
3. **Check it:**

```
python check_data.py --tf M1
python check_m1_vs_m5.py
```

   `check_m1_vs_m5.py` builds M5 bars out of your M1 bars and compares them with your stored M5 bars. Expect
   `OK: M1 agrees with M5 on 99.xx% ...`. A `CHECK:` means the M1 data or its time labels are wrong: paste the output to me
   and do not run any scalping test until it is OK.

## Appendix E - Test the scalper (S7, M1 data)

Do Appendix D first and make sure `check_m1_vs_m5.py` says OK. All commands run from the project root with the
virtual environment active.

```
python tests\test_strategies.py            # must pass, now includes the three scalper modes
cd s7_scalper
python run.py --research --out results\1_baseline
python run.py --research --baseline 100 --out results\2_random_baseline
python run.py --research --cost-mult 2 --out results\3_cost_x2
python run.py --research --grid --walkforward --out results\4_grid_walkforward
python run.py --out results\5_real_account
```

Try the other entry style with `--set mode=pullback` (or `--set mode=both`) added to any of those commands, and put a
prefix on the output folder so runs do not overwrite each other, for example `--out results\pullback_1_baseline`.

How to read it:
- The number that matters is **exp R at cost x2** (run 3). Positive there means some margin for worse fills than the backtest assumed.
- Check **trades**: with M1 data a real result needs hundreds of trades; below about 400 out-of-sample trades treat it as noise.
- Walk-forward uses 6 months of training and 2 of testing. If your M1 history is short, add `--train-months 4 --test-months 2`.
- The real-account run (run 5) uses 0.01 lot with the $1.00 minimum stop, so it can trade, but it halts when equity reaches the floor buffer. That is expected, and is the same rule every other bot follows.
- Paste the console summaries here and I will interpret them, as with the other bots.

If `run.py` stops with "No XAUUSD M1 candles found", the M1 data is not loaded: repeat Appendix D.

