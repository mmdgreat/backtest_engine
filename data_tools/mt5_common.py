"""Shared MT5 helpers."""
import sys

import MetaTrader5 as mt5

import config

TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}
TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}


def connect_mt5():
    """Attach to the already-logged-in terminal. No credentials are needed or stored."""
    if not mt5.initialize(path=config.MT5_TERMINAL_PATH):
        sys.exit(f"MT5 initialize failed: {mt5.last_error()}")
    if mt5.symbol_info(config.SYMBOL) is None:
        sys.exit(f"Symbol {config.SYMBOL} not found at this broker. Check the name in Market Watch.")
    if not mt5.symbol_select(config.SYMBOL, True):
        sys.exit(f"Could not select {config.SYMBOL}: {mt5.last_error()}")
