"""S6 Volatility Squeeze Breakout bot. Run:  python run.py --help

Everything this strategy does lives in this folder: params.py (settings you tune), strategy.py (the rules),
tuning_log.md (your notes), results/ (one sub-folder per run). The shared engine is in ../botcore."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import params  # noqa: E402
import strategy  # noqa: E402
from botcore.cli import main  # noqa: E402

if __name__ == "__main__":
    main(params, strategy)
