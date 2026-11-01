"""Central settings for the XAUUSD bot. Edit these; nothing else needs touching."""
import os

MT5_TERMINAL_PATH = r"C:\Program Files\Vantage International MT5\terminal64.exe"
SYMBOL = "XAUUSD"  # check the exact name with mt5_check.py (brokers sometimes use suffixes)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "trading"
CANDLES_COLLECTION = "candles"
SPECS_COLLECTION = "symbol_specs"

DEFAULT_TIMEFRAMES = ["M5"]
DEFAULT_SINCE = "2024-11-15"  # used only when a timeframe has no data in MongoDB yet
