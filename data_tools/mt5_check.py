"""Phase 0 check: connects to MT5 and prints what the bot needs to know.

Run:  python mt5_check.py
Most important line: the account TYPE. The bot must only ever run on DEMO.
"""
import time
from datetime import datetime, timezone

import MetaTrader5 as mt5

import config
from mt5_common import connect_mt5


def main():
    connect_mt5()
    term = mt5.terminal_info()
    acc = mt5.account_info()
    info = mt5.symbol_info(config.SYMBOL)
    tick = mt5.symbol_info_tick(config.SYMBOL)

    modes = {
        mt5.ACCOUNT_TRADE_MODE_DEMO: "DEMO",
        mt5.ACCOUNT_TRADE_MODE_CONTEST: "CONTEST",
        mt5.ACCOUNT_TRADE_MODE_REAL: "REAL",
    }
    mode = modes.get(acc.trade_mode, str(acc.trade_mode))

    print("== Terminal ==")
    print(f"  name: {term.name} | build: {term.build} | connected: {term.connected}")
    print(f"  algo trading allowed in terminal: {term.trade_allowed}")
    print("== Account ==")
    print(f"  login: {acc.login} | server: {acc.server} | type: {mode}")
    print(f"  balance: {acc.balance} {acc.currency} | leverage: 1:{acc.leverage}")
    if mode != "DEMO":
        print("  !! WARNING: this is NOT a demo account. Do not run the bot on it.")

    print(f"== {config.SYMBOL} ==")
    for field in (
        "digits", "point", "trade_contract_size", "volume_min", "volume_max",
        "volume_step", "spread", "trade_stops_level", "trade_freeze_level",
        "filling_mode", "swap_long", "swap_short",
    ):
        print(f"  {field}: {getattr(info, field)}")

    # Broker server clock vs real UTC (only meaningful while the market is open)
    if tick is not None:
        diff_h = (tick.time - time.time()) / 3600
        offset = round(diff_h)
        if abs(diff_h) > 12:
            print("  server time offset: market looks closed; re-run while gold is trading")
        else:
            print(f"  server time offset vs UTC: about {offset:+d} h "
                  f"(stored candle times are in this server time, not true UTC)")
        print(f"  last tick: bid {tick.bid} ask {tick.ask} at "
              f"{datetime.fromtimestamp(tick.time, tz=timezone.utc):%Y-%m-%d %H:%M:%S} (server clock)")

    rates = mt5.copy_rates_from_pos(config.SYMBOL, mt5.TIMEFRAME_M5, 0, 3)
    print("== Latest M5 bars ==")
    if rates is None:
        print(f"  could not read bars: {mt5.last_error()}")
    else:
        for r in rates:
            t = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
            print(f"  {t:%Y-%m-%d %H:%M} O {r['open']} H {r['high']} L {r['low']} C {r['close']} spread {r['spread']}")

    mt5.shutdown()


if __name__ == "__main__":
    main()
