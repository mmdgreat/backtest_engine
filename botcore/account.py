"""Account and cost rules. The real-account preset is the one the user specified:
$100 start, equity must never fall below $70, 1 pip = 1.00 price move = $1 per 0.01 lot."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AccountConfig:
    initial_capital: float = 100.0
    equity_floor: float = 70.0          # no trade may be taken that could end below this
    halt_buffer: float = 1.0            # bot halts for good once equity <= floor + buffer
    risk_pct: float = 0.05              # max risk per trade, share of equity (or of initial if not compounding)
    compounding: bool = True
    max_daily_loss_pct: float = 0.10    # no new entries for the trading day after this much realised loss
    contract_size: float = 100.0        # ounces per 1.00 lot -> $100 per $1 move per lot
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 1.0
    pip_size: float = 1.0               # price units per pip (user rule: 1 pip = 1 USD per oz)
    label: str = "account"


@dataclass(frozen=True)
class CostModel:
    commission_per_lot_per_side: float = 0.0   # Standard STP = 0. Raw/ECN accounts: set e.g. 3.0
    slippage_market: float = 0.05              # price units, adverse, on market entries and time exits
    slippage_stop: float = 0.10                # price units, adverse, on stop-loss fills
    max_spread: float = 0.50                   # skip entries when the bar's spread exceeds this (price units)
    min_stop: float = 0.50                     # skip entries whose stop is closer than this to the fill
    cost_mult: float = 1.0                     # stress test: multiplies spread and slippage (use 2.0)
    # Overnight swap per ounce, price units (-0.20 = pay $0.20 per oz per night, about -20 points; $0.20 per
    # night on a 0.01 lot). Only charged when a position is held across the 5pm New York rollover (Wednesday
    # counts triple). Both sides default to a cost because the real numbers are broker specific:
    # read them with data_tools/mt5_check.py (swap_long / swap_short, in points) and edit here.
    swap_long: float = -0.20
    swap_short: float = -0.20
    swap_wed_mult: int = 3


REAL = AccountConfig()

# Edge-testing account: a huge virtual balance with a fixed $1,000 risk per trade (0.1% of $1,000,000), no floor,
# no daily-loss stop. The balance is large enough that a losing strategy cannot run out of money, so EVERY signal
# in the whole history is tested (a small virtual account gets wiped out and silently stops trading, which hides
# the later years). Lots are not capped in practice and the 0.01 minimum is negligible at this size.
# Used only to judge a strategy in R-multiples; the REAL account answers whether $100 / $70 can trade it.
RESEARCH = AccountConfig(
    initial_capital=1_000_000.0, equity_floor=0.0, halt_buffer=0.0, risk_pct=0.001,
    compounding=False, max_lot=100.0, max_daily_loss_pct=1.0, label="research",
)


def with_overrides(acct, capital=None, floor=None, risk_pct=None):
    kw = {}
    if capital is not None:
        kw["initial_capital"] = float(capital)
    if floor is not None:
        kw["equity_floor"] = float(floor)
    if risk_pct is not None:
        kw["risk_pct"] = float(risk_pct)
    return replace(acct, **kw) if kw else acct
