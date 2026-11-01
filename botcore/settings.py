"""Settings shared by every bot. Edit here only for broker / database differences."""
import os

SYMBOL = "XAUUSD"
TIMEFRAME = "M5"               # base timeframe stored in MongoDB; everything else is built from it
POINT = 0.01                   # price value of one MT5 "point" (XAUUSD has 2 digits at most brokers)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "trading"
CANDLES_COLLECTION = "candles"

# Broker server clock. Most MT5 brokers (Vantage included) roll the trading day at 5pm New York,
# which makes server time = New York time + 7 hours all year (UTC+2 in winter, UTC+3 in summer).
# Run `python -m botcore.check_clock` to confirm this against your own data.
SERVER_MINUS_NY_HOURS = 7
