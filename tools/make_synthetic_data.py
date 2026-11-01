"""Write synthetic XAUUSD M5 candles (broker server clock) to a CSV, to test the pipeline offline.

The data is a random walk with realistic session volatility, spreads and market hours. It contains NO edge,
so a sound strategy should NOT look profitable on it. Use it only to check that the code runs.

    python tools/make_synthetic_data.py --out synthetic_m5.csv --start 2024-11-15 --days 700 --seed 1
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from botcore.synthetic import make  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="synthetic_m5.csv")
    ap.add_argument("--start", default="2024-11-15")
    ap.add_argument("--days", type=int, default=700)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--trend", type=float, default=0.0,
                    help="0 = pure random walk (no edge); 0.3 = planted momentum for a positive control")
    a = ap.parse_args()
    df = make(a.start, a.days, a.seed, trend=a.trend)
    df.to_csv(a.out, index=False)
    print(f"wrote {len(df):,} bars to {a.out}  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")
