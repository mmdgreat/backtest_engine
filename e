warning: in the working copy of 'DEPLOY_GUIDE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'README.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'STRATEGY_RULES.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/__init__.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/account.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/check_clock.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/cli.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/data.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/indicators.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/metrics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/report.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/sessions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/settings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/signals.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/synthetic.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/util.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'botcore/walkforward.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/check_data.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/config.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/mt5_check.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/mt5_common.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/requirements.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data_tools/sync_candles.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's1_orb/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's1_orb/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's1_orb/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's1_orb/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's2_liquidity_sweep/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's2_liquidity_sweep/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's2_liquidity_sweep/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's2_liquidity_sweep/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's3_trend_pullback/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's3_trend_pullback/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's3_trend_pullback/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's3_trend_pullback/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's4_donchian_h4/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's4_donchian_h4/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's4_donchian_h4/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's4_donchian_h4/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's5_mean_reversion/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's5_mean_reversion/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's5_mean_reversion/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's5_mean_reversion/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's6_squeeze_breakout/params.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's6_squeeze_breakout/run.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's6_squeeze_breakout/strategy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 's6_squeeze_breakout/tuning_log.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_strategies.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tools/make_synthetic_data.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/DEPLOY_GUIDE.md b/DEPLOY_GUIDE.md[m
[1mindex c1a1017..02efdc5 100644[m
[1m--- a/DEPLOY_GUIDE.md[m
[1m+++ b/DEPLOY_GUIDE.md[m
[36m@@ -380,4 +380,30 @@[m [mC:\xauusd-bots\[m
       results\<name>\    report.md, trades.csv, summary.json, equity.png, grid.csv, walkforward_*.csv[m
 ```[m
 [m
[32m+[m[32m## Appendix D - Load M1 candles (needed before any scalping test)[m
 [m
[32m+[m[32mThe six bots use M5. A scalper needs M1, and your broker may keep less M1 history than M5. Do this once.[m
[32m+[m
[32m+[m[32m1. **Let MT5 hold the history.** In MT5: Tools > Options > Charts > set *Max bars in chart* to **Unlimited** and press OK.[m
[32m+[m[32m   Open an XAUUSD **M1** chart and press the **Home** key a few times (or hold it) so the terminal downloads older bars.[m
[32m+[m[32m   Keep MT5 open and logged in to your Vantage demo account.[m
[32m+[m[32m2. **Load it into MongoDB** (about 1.7 million bars for five years; it can take several minutes):[m
[32m+[m
[32m+[m[32m```[m
[32m+[m[32mcd data_tools[m
[32m+[m[32mpython sync_candles.py --tf M1 --since 2021-01-04[m
[32m+[m[32m```[m
[32m+[m
[32m+[m[32m   It prints progress, then `now stored: ... bars, oldest ...`. If it prints a WARNING that the oldest bar is later than[m
[32m+[m[32m   2021-01-04, the broker simply does not hold that much M1 history: that is fine, scalp tests will then cover the years[m
[32m+[m[32m   available. Running the same command again later adds only newer bars.[m
[32m+[m[32m3. **Check it:**[m
[32m+[m
[32m+[m[32m```[m
[32m+[m[32mpython check_data.py --tf M1[m
[32m+[m[32mpython check_m1_vs_m5.py[m
[32m+[m[32m```[m
[32m+[m
[32m+[m[32m   `check_m1_vs_m5.py` builds M5 bars out of your M1 bars and compares them with your stored M5 bars. Expect[m
[32m+[m[32m   `OK: M1 agrees with M5 on 99.xx% ...`. A `CHECK:` means the M1 data or its time labels are wrong: paste the output to me[m
[32m+[m[32m   and do not run any scalping test until it is OK.[m
[1mdiff --git a/README.md b/README.md[m
[1mindex 070ae4c..191e1fb 100644[m
[1m--- a/README.md[m
[1m+++ b/README.md[m
[36m@@ -20,7 +20,7 @@[m [ms6_squeeze_breakout/     Volatility Squeeze / NR7 Breakout[m
     run.py               the command line for this bot[m
     tuning_log.md        your notes, one row per run[m
     results/             created on the first run: one sub-folder per run[m
[31m-data_tools/              Phase 1: MT5 check, sync candles to MongoDB, data quality check[m
[32m+[m[32mdata_tools/              Phase 1: MT5 check, sync candles to MongoDB, data quality check, M1-vs-M5 check[m
 tests/                   engine tests and strategy look-ahead tests[m
 tools/                   synthetic data generator (for offline code checks only)[m
 ```[m
[1mdiff --git a/data_tools/sync_candles.py b/data_tools/sync_candles.py[m
[1mindex 1aba098..43ab50c 100644[m
[1m--- a/data_tools/sync_candles.py[m
[1m+++ b/data_tools/sync_candles.py[m
[36m@@ -3,6 +3,7 @@[m
 Safe to run repeatedly: it resumes from the newest stored bar and upserts, so no duplicates.[m
 Run:  python sync_candles.py                 (default timeframes from config.py)[m
       python sync_candles.py --tf M1 M5 H1   (several timeframes)[m
[32m+[m[32m      python sync_candles.py --tf M1 --since 2021-01-04   (first M1 load: about 1.7M bars for 5 years, takes a while)[m
       python sync_candles.py --since 2022-01-01   (used only for a timeframe with no data yet)[m
       python sync_candles.py --backfill --since 2021-01-01   (load OLDER history before your oldest stored bar)[m
 [m
[36m@@ -65,9 +66,12 @@[m [mdef sync_timeframe(coll, symbol, tf, since, backfill=False):[m
     newest_complete = end - timedelta(seconds=tf_sec)  # a bar is final only once it has closed[m
 [m
     print(f"[{tf}] from {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M} (server time)")[m
[31m-    cursor, total = start, 0[m
[32m+[m[32m    cursor, total, n_chunks = start, 0, 0[m
     step = timedelta(days=CHUNK_DAYS[tf])[m
     while cursor < end:[m
[32m+[m[32m        n_chunks += 1[m
[32m+[m[32m        if n_chunks % 25 == 0:[m
[32m+[m[32m            print(f"  ... {cursor:%Y-%m-%d} reached, {total:,} bars so far")[m
         chunk_end = min(cursor + step, end + timedelta(minutes=1))[m
         rates = mt5.copy_rates_range(symbol, TF_MAP[tf], cursor, chunk_end)[m
         if rates is None:[m
[36m@@ -96,6 +100,15 @@[m [mdef sync_timeframe(coll, symbol, tf, since, backfill=False):[m
                 total += len(ops)[m
         cursor = chunk_end[m
     print(f"[{tf}] upserted {total} bars")[m
[32m+[m[32m    oldest = coll.find_one({"symbol": symbol, "tf": tf}, sort=[("time", 1)])[m
[32m+[m[32m    stored = coll.count_documents({"symbol": symbol, "tf": tf})[m
[32m+[m[32m    if oldest:[m
[32m+[m[32m        print(f"[{tf}] now stored: {stored:,} bars, oldest {oldest['time']}")[m
[32m+[m[32m        if not backfill and as_utc(oldest["time"]) - since > timedelta(days=14):[m
[32m+[m[32m            print(f"[{tf}] WARNING: the oldest bar is later than --since {since:%Y-%m-%d}. The broker/terminal only holds "[m
[32m+[m[32m                  f"history from about {oldest['time']:%Y-%m-%d}. If you need more, open a {tf} chart in MT5, set "[m
[32m+[m[32m                  "Tools > Options > Charts > Max bars in chart = Unlimited, press Home on the chart to download "[m
[32m+[m[32m                  "history, then run this again.")[m
 [m
 [m
 def save_specs(db, symbol):[m
