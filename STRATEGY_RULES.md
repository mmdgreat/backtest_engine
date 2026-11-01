# XAUUSD Strategy Rules

One document for all six bots. Part A is the rules every bot shares (account, costs, fills, testing).
Part B is one section per strategy: what it does, the exact entry/stop/exit rules, its default settings
and what to tune. The numbers here match `params.py` in each strategy folder; if you change a `params.py`
value, update the table here too.

Status: all six bots are built, tested for look-ahead and run end to end on synthetic data.
**None has been run on your real candles yet, so nothing here says whether any strategy has an edge.**

---

# Part A - Rules shared by every bot

## A1. Data and time

| Item | Rule |
| --- | --- |
| Symbol / timeframe | XAUUSD, M5 candles from MongoDB `trading.candles` (or a CSV with `--source csv`) |
| Price | Candle prices are **bid**. Spread comes from each candle's `spread` field (points, 1 point = 0.01) |
| Broker clock | Stored `time` is broker server time. Assumed **server = New York + 7 hours** all year (day rolls at 17:00 New York). Verify with `python -m botcore.check_clock` |
| Session times | London and New York session times are in **local exchange time** (DST handled), converted from the broker clock |
| Higher timeframes | H1/H4/D1 are built from M5 on the broker clock. A higher-timeframe bar is only visible **after it has closed**, never before |
| Look-ahead | Signals on bar *i* use only bars up to and including *i*. `tests/test_strategies.py` proves this by cutting the data and comparing signals |

## A2. Account (your rules)

| Item | Rule |
| --- | --- |
| Starting capital | **$100** |
| Equity floor | **Equity must never go below $70.** Every trade is sized so its planned loss fits in (equity - $70). The bot also halts for good once equity is at or below $71 |
| Pip | 1 pip = a 1.00 price move = $1 per ounce. A 0.01 lot is 1 ounce, so **0.01 lot gains or loses $1 per 1.00 move** |
| Lot sizes | Minimum 0.01, step 0.01, maximum 1.0, rounded **down** |
| Risk per trade | 5% of equity (never less than 5% of the starting $100 = $5), capped at the room above the floor |
| Compounding | Risk grows with equity above $100; it never shrinks below $5 until the floor cap takes over |
| Daily loss limit | No new entries for the rest of a trading day after losing 10% of that day's starting equity |
| Max trades per day | Set per strategy (see Part B) |
| One position at a time | A new signal is only taken after the previous trade has closed |

**What this means in practice.** There is only $30 of room above the floor and the smallest trade is 0.01 lot.
A stop wider than about **$4.90** cannot be taken at the start (5% of $100 = $5 of risk at $1 per $1 move) and the
account survives only about six full stop-outs in a row. Strategies with wide stops (S4 especially) will skip most
or all signals on this account. That is the rule working, not a bug. It also means $100/$70 is a poor account to
*judge* an edge on, so each bot has a second mode (A5).

## A3. Costs and fills

| Item | Rule |
| --- | --- |
| Entry | Signal known at the **close** of bar *i*; market order filled at the **open of bar i+1** |
| Buy / sell price | Longs buy at ask (bid + that bar's spread). Shorts sell at bid. A short's stop and target trigger on the ask |
| Slippage | 0.05 on market entries and time exits; 0.10 on stop-loss fills; none on target (limit) fills |
| Same bar touches stop and target | **The stop is assumed to hit first** |
| Gap through a stop | Fills at the open of the gap, not at the stop price |
| Spread filter | No entry when the bar's spread is above 0.50 (each strategy may set a tighter limit) |
| Minimum stop | Entries with a stop closer than 0.50 are skipped |
| Commission | $0 (Standard STP assumed). For a Raw/ECN account set `commission_per_lot_per_side` in `botcore/account.py` |
| Swap | -0.20 per ounce per night when a position crosses the 17:00 New York rollover (triple on Wednesday). Broker specific: read yours with `data_tools/mt5_check.py` and edit `botcore/account.py` |
| Weekend / market breaks | Trades are closed before any data gap longer than 30 minutes (S4 is the exception and may hold over weekends) |

## A4. Testing protocol (same for every strategy)

1. **Baseline run** on the full history with default settings. Read `report.md`.
2. **Random-direction baseline** (`--baseline 100`): same entries, same stops, coin-flip direction. A strategy must beat this clearly.
3. **Cost stress** (`--cost-mult 2`): spread and slippage doubled. It should still be positive.
4. **Small grid** (`--grid`): the 12-24 combinations listed in each section. A real edge is a *cluster* of nearby settings that all work, not one lucky row.
5. **Walk-forward** (`--walkforward`): choose the best setting on 6 months, test it on the next 2 months, roll forward. **Only the out-of-sample result counts.**
6. **Pass bar** (proposed, change it if you disagree): out-of-sample expectancy **above +0.10 R** per trade after costs, profit factor **above 1.2**, at least **200 trades** (S4 and S6: at least 60, they trade rarely), positive in most walk-forward windows, still positive at cost x2, and better than the random baseline.
7. Tune **one parameter at a time** and write each run in that bot's `tuning_log.md`.

**Why the protocol is this strict.** On a pure random walk with no edge (synthetic seed 2), S4's grid showed 11 of
12 settings positive and a best row of +0.29 R, PF 1.85. Its walk-forward out-of-sample result was +0.23 R over only
30 trades, carried by a single 5-trade window while the other two windows lost. A good-looking grid or a small
out-of-sample sample is not evidence. Trust a result only when it has enough trades, holds in most windows, survives
doubled costs and beats the random baseline.

## A5. Two account modes

| Mode | Command | Purpose |
| --- | --- | --- |
| Real account | `python run.py` | Your rules: $100, floor $70, 5% risk, 0.01 lot minimum. Shows what would actually happen |
| Research account | `python run.py --research` | Virtual $1,000,000, fixed $1,000 (0.1%) risk per trade, no floor, no daily-loss stop, so the account cannot be wiped out and the whole history is tested. Judges the edge in R-multiples without the 0.01-lot minimum distorting results. The grid and walk-forward always use this mode |

Judge edge in research mode first; use the real mode to see whether the account rules leave room to trade it.

## A6. Known limits

- **No news blackout.** There is no economic calendar in the data. Scheduled events (NFP, CPI, FOMC) are not avoided. Add a blackout list before any live use.
- **M5 candles hide what happens inside a bar.** The stop-first rule is conservative. Re-test finalists on M1 data.
- **Candles are bid.** Ask is bid + the stored spread, which is an approximation.
- **Demo/backtest fills are kinder than live fills**, especially around news.
- Synthetic data (`tools/make_synthetic_data.py`) checks that the code runs and is unbiased. It says nothing about gold.

# Part B - Strategy rules

Folder, settings file, rules file and run command for each bot:

| Bot | Folder | Run from inside the folder |
| --- | --- | --- |
| S1 Opening Range Breakout | `s1_orb/` | `python run.py` |
| S2 Liquidity Sweep + Reversal | `s2_liquidity_sweep/` | `python run.py` |
| S3 Trend Pullback | `s3_trend_pullback/` | `python run.py` |
| S4 Donchian H4 Breakout | `s4_donchian_h4/` | `python run.py` |
| S5 Mean Reversion (Asian) | `s5_mean_reversion/` | `python run.py` |
| S6 Squeeze Breakout / NR7 | `s6_squeeze_breakout/` | `python run.py` (add `--set mode=nr7` for NR7) |

Each folder has `params.py` (settings you tune), `strategy.py` (the rules in code), `run.py`, `tuning_log.md` and a
`results/` folder that fills with one sub-folder per run (report, trades, equity curve). Bots do not import
each other; they share only the frozen engine in `botcore/`.

## S1 - Opening Range Breakout (`s1_orb/`)

**Idea.** The first minutes after a session opens set a range. A close beyond it, soon after, often carries on.
This is the simple baseline the other strategies must beat.

**Rules**
1. Two sessions are traded: **London** (range starts 08:00 London time) and **New York** (range starts 08:20 New York time, the COMEX gold open).
2. Opening range = high and low of the first **30 minutes** (60 is the alternative).
3. Entry window: the first M5 **close** beyond the range within **120 minutes** after the range ends. Close above = long, below = short. Only the first break per session per day counts.
4. Filter: the range must be between **2 and 15 ATRs** wide (ATR = 14 bars on M5). Too narrow is noise, too wide has already moved.
5. Stop: **2.0 x ATR** from entry (alternative `stop_mode=range`: the far side of the range).
6. Target: **2.0 x the stop distance**.
7. Exit: target, stop, **48 bars (4 hours)**, or flat by **16:30 New York**, whichever comes first.
8. Limits: **2 trades per day**, one per session.

| Setting | Default | Meaning |
| --- | --- | --- |
| `sessions` | london, ny | Which opens to trade |
| `range_min` | 30 | Opening range length (minutes) |
| `entry_window_min` | 120 | How long after the range a break may be taken |
| `stop_mode` / `atr_mult` | atr / 2.0 | Stop distance |
| `rr` | 2.0 | Target as a multiple of the stop |
| `min_range_atr` / `max_range_atr` | 2.0 / 15.0 | Range-size filter |
| `max_hold_bars` | 48 | Time stop |

**Grid (18 runs):** `range_min` 30/60 x `atr_mult` 1.5/2.0/3.0 x `rr` 1.5/2.0/3.0.
**Watch for:** false breaks right at the open (spread is widest then); results that depend on one session only; a range filter that only works for one value.
**Account note:** a 2-ATR stop on M5 gold is typically a few dollars, so signals on volatile days will exceed the $4.90 limit of the real account (the run summary counts these as `stop_too_wide_for_risk`; check the count on your own data).

## S2 - Liquidity Sweep + Reversal (`s2_liquidity_sweep/`)

**Idea (SMC/ICT).** Price often raids obvious stops above a high or below a low, then reverses. The reversal is
confirmed when price breaks the last minor swing in the new direction. Your original rule set was not available to
me in this session, so **these rules are my explicit version for you to review and correct**.

**Liquidity pools:** Asian range high/low (00:00-07:00 London), previous trading day high/low, London session high/low (07:00-12:00 London, usable for New York sweeps).

**Rules**
1. Kill zones only: **07:00-11:00 London** and **08:00-12:00 New York**.
2. **Sweep:** price trades beyond a pool by at least **0.15 ATR**, then a bar **closes back inside** the pool within **3 bars**. Closing back inside separates a sweep from a breakout.
3. **Structure shift:** within **24 bars** of the sweep, a bar closes through the last confirmed M5 swing point on the other side. High swept: close below the last swing low = short. Low swept: close above the last swing high = long. A swing needs **3 lower highs / higher lows on each side**, so it is only known 3 bars later.
4. If price takes out the sweep extreme first, the setup is cancelled.
5. Stop: **0.25 ATR** beyond the sweep extreme. Target: **2.0 x the stop distance**.
6. Exit: target, stop, **48 bars**, or flat by **16:30 New York**. Each pool is used once per kill zone per day. **2 trades per day.**

| Setting | Default | Meaning |
| --- | --- | --- |
| `levels` | asia, prev_day, london | Pools to watch |
| `sweep_min_atr` | 0.15 | Minimum push beyond the level |
| `max_return_bars` | 3 | Bars allowed to close back inside |
| `swing_k` | 3 | Swing strength |
| `max_shift_bars` | 24 | Time allowed for the structure shift |
| `sl_buf_atr` / `rr` | 0.25 / 2.0 | Stop buffer / target multiple |

**Grid (24 runs):** `sweep_min_atr` 0.1/0.25 x `max_shift_bars` 12/24 x `sl_buf_atr` 0.15/0.4 x `rr` 1.5/2.0/3.0.
**Watch for:** it is the most rule-heavy strategy, so it is the easiest to overfit; check each pool type separately (the report splits results by pool); stops are often wider than the real account allows.

## S3 - Trend Pullback (`s3_trend_pullback/`)

**Idea.** Trade with the hourly trend, entering when price pulls back to a moving average and turns.

**Rules**
1. Trend, from **completed H1 bars**: fast EMA (50) above slow EMA (200) and the fast EMA rising over the last 3 H1 bars = up. Below and falling = down. Anything else = no trade.
2. Pullback on M5: in an uptrend, a bar whose low reaches the **20-period M5 EMA + 0.25 ATR** and **closes back above the EMA on a bullish candle**. Shorts mirror this.
3. It must be a real pullback: in the previous **24 bars** price was at least **1.0 ATR** away from the EMA on the trend side.
4. Only enter **03:00-12:00 New York**. Spread must be at most 0.40. Wait **12 bars (1 hour)** after a signal before the next one.
5. Stop: **1.5 x ATR** from entry. Target: **2.0 x the stop distance**. Optional chandelier trail (`trail_atr`, off by default).
6. Exit: target, stop, **96 bars (8 hours)**, or flat by **16:30 New York**. **3 trades per day.**

| Setting | Default | Meaning |
| --- | --- | --- |
| `h1_fast` / `h1_slow` / `slope_bars` | 50 / 200 / 3 | Trend definition |
| `pull_ema` / `band_atr` | 20 / 0.25 | Pullback level |
| `ext_lookback` / `min_ext_atr` | 24 / 1.0 | Required prior extension |
| `stop_atr` / `rr` / `trail_atr` | 1.5 / 2.0 / 0 | Risk and reward |
| `window_ny` / `cooldown_bars` | 03:00-12:00 / 12 | When and how often |

**Grid (18 runs):** `pull_ema` 20/50 x `stop_atr` 1.0/1.5/2.0 x `rr` 1.5/2.0/3.0.
**Watch for:** it trades often, so costs matter most here; trades clustered in one strong trend; the trend filter lagging at turning points.

## S4 - Donchian / H4 Breakout (`s4_donchian_h4/`)

**Idea.** A slow trend follower. Gold's big moves come in a few long trends; ride them with a trailing stop and accept many small losses.

**Rules**
1. On each **completed H4 bar**: close above the highest high of the previous **20 H4 bars** = long; below the lowest low = short. (55 is the slower alternative.)
2. Filter: only trade with the **H4 EMA(200)** (price above for longs, below for shorts). Set `ema_filter=0` to turn it off.
3. Stop and trail: **3.0 x H4 ATR** from entry, then trailing behind the best price by the same distance (chandelier exit). **No fixed target.**
4. Exit: trail, or **10 days** maximum. May hold over weekends (swap is charged for each night held). **1 trade per day.**

| Setting | Default | Meaning |
| --- | --- | --- |
| `channel` | 20 | Donchian length (H4 bars) |
| `atr_mult` | 3.0 | Stop and trail distance (H4 ATRs) |
| `ema_filter` | 200 | Trend filter (0 = off) |
| `allow_long` / `allow_short` | True / True | Direction switches |
| `max_hold_days` | 10 | Time stop |

**Grid (12 runs):** `channel` 20/55 x `atr_mult` 2.5/3.0/4.0 x `ema_filter` 0/200.
**Walk-forward for this bot:** it makes only about 25-35 trades a year, so the default 6-month training window never reaches the 30-trade minimum and every window sits out. Use longer windows and a lower minimum: `python run.py --research --grid --walkforward --train-months 12 --test-months 4 --min-trades 20`, and use 3+ years of data.
**Watch for:** very few trades a year, so you need years of data (60+ trades before trusting anything); a low win rate of 30-40% is normal for this style; long losing streaks.
**Account note:** an H4 ATR on gold is typically well over $10, so a 3-ATR stop is $30 or more, far beyond the $4.90 the real account can risk. **Expect this strategy to skip nearly every signal on the $100 / $70 account at 0.01 lot** (on synthetic data it took none). Judge it in research mode, then decide how to handle that gap.

## S5 - Mean Reversion, Asian session (`s5_mean_reversion/`)

**Idea.** In the quiet, choppy Asian session, price that stretches outside its Bollinger band tends to snap back to the middle.

**Rules**
1. Only inside **00:00-07:00 London** time.
2. Quiet and choppy only: **efficiency ratio (48 bars) below 0.30** and **ATR not above 1.3 x its one-day average**.
3. Entry: the previous bar closed **outside** the (20, 2.0) Bollinger band and this bar closes **back inside**. Below the lower band = long, above the upper = short.
4. Target: the Bollinger **mid-band** at the signal.
5. Stop: beyond the extreme of the last 3 bars plus **0.5 ATR**.
6. Skip the trade when the distance to the mid-band is less than **0.8 x** the stop distance. Spread must be at most 0.35.
7. Exit: target, stop, **36 bars (3 hours)**, or the end of the Asian window. **2 trades per day.**

| Setting | Default | Meaning |
| --- | --- | --- |
| `window_london` | 00:00-07:00 | Trading window |
| `bb_len` / `bb_k` | 20 / 2.0 | Bollinger band |
| `er_len` / `er_max` | 48 / 0.30 | Choppiness filter |
| `max_atr_ratio` | 1.3 | Volatility-spike filter |
| `stop_buf_atr` / `min_rr` | 0.5 / 0.8 | Stop buffer / minimum reward-to-risk |

**Grid (18 runs):** `bb_k` 2.0/2.5 x `er_max` 0.2/0.3/0.4 x `stop_buf_atr` 0.3/0.5/1.0.
**Watch for:** high win rate with rare large losses (the dangerous profile); **no news blackout**, and early-morning Asian news can move gold hard; planted momentum in test data destroys it, which is expected.

## S6 - Volatility Squeeze Breakout / NR7 (`s6_squeeze_breakout/`)

**Idea.** Quiet periods precede big moves. Detect the quiet, then trade the first break out of it.

**Squeeze mode (default).** On completed **15-minute** bars (60 is the alternative):
1. Squeeze = Bollinger Bands (20, 2.0) **entirely inside** Keltner Channels (20, 1.5 ATR).
2. After a squeeze of at least **6 bars** releases, the first bar within **3 bars** that closes beyond the previous bar's extreme **and** on the same side of the Bollinger mid-line is the signal (up = long).
3. Only enter **03:00-12:00 New York**, spread at most 0.40.
4. Stop: **1.5 x ATR** (of the squeeze timeframe). Target: **2.0 x the stop distance**. Time stop: **8 squeeze-timeframe bars**; flat by **16:30 New York**. **2 trades per day.**

**NR7 mode (`--set mode=nr7`).**
1. A day is NR7 when its range is the smallest of the last 7 days (broker-day bars).
2. The next trading day, the first M5 **close** beyond the NR7 day's high (long) or low (short), inside 03:00-12:00 New York, is the signal.
3. Stop: the **far side** of the NR7 range (`nr7_stop=mid` uses the middle). Target: 2.0 x the stop distance. Flat by 16:30 New York.

| Setting | Default | Meaning |
| --- | --- | --- |
| `mode` | squeeze | `squeeze` or `nr7` |
| `tf_min` | 15 | Squeeze bar size (minutes) |
| `kc_mult` | 1.5 | Keltner width |
| `min_squeeze` / `follow_bars` | 6 / 3 | Squeeze length / breakout deadline |
| `stop_atr` / `rr` | 1.5 / 2.0 | Risk and reward |
| `nr7_lookback` / `nr7_stop` | 7 / opposite | NR7 settings |

**Grid (18 runs, squeeze mode):** `tf_min` 15/60 x `min_squeeze` 4/6/10 x `rr` 1.5/2.0/3.0.
**Watch for:** few signals (on 700 days of synthetic data: roughly 120-150 trades in squeeze mode and 60-75 in NR7 mode), so confidence intervals are wide; false breakouts at the squeeze release; NR7 stops equal to a small daily range may be too tight (`stop_too_tight` skips).

---

# Part C - Order of work

1. Install and run `python tests/test_engine.py` and `python tests/test_strategies.py` (both must pass).
2. Sync your real candles (data tools) and run `python -m botcore.check_clock` to confirm the server-time offset.
3. For each strategy in the order S1, S2, S3, S4, S5, S6: baseline (research mode), `--baseline 100`, `--cost-mult 2`, `--grid`, `--walkforward`, then the real-account run.
4. Record every run in that bot's `tuning_log.md`. Drop any strategy that fails the pass bar in A4.
5. Only strategies that pass go forward to demo trading.


