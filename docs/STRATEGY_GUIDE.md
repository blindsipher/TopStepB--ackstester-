# TopStepB Strategy Development Guide

**Goal:** Create institutional-grade trading strategies that integrate with the TopStepB pipeline.

---

## Quick Reference

**Required files for any strategy:**
```
strategies/{strategy_name}/
├── __init__.py
├── strategy.py                 # Vectorized logic (optimization)
├── parameters.py               # Parameter ranges
├── indicators.py               # VectorBT-based indicators
└── deployment_template.py      # Stateful logic (live trading)
```

**Key constraint:** Vectorized and stateful implementations MUST produce identical signals.

---

## The Dual-Implementation Model

Every strategy exists in TWO forms:

### 1. Vectorized Implementation (`strategy.py`)
**Purpose:** High-speed optimization (1000+ trials/min)
**Method:** Process entire dataset at once using pandas/VectorBT
**Usage:** Training and parameter discovery

```python
class MyStrategy(TradingStrategy):
    def generate_signals(self, data, params, config):
        # Calculate indicators
        sma_fast = data['close'].rolling(params['fast_period']).mean()
        sma_slow = data['close'].rolling(params['slow_period']).mean()

        # CRITICAL: Use .shift(1) to prevent look-ahead bias
        long_entry = sma_fast.shift(1) > sma_slow.shift(1)

        signals = pd.Series(0, index=data.index)
        signals[long_entry] = 1
        return signals
```

### 2. Stateful Implementation (`deployment_template.py`)
**Purpose:** Live trading execution and validation
**Method:** Process data bar-by-bar, maintaining state
**Usage:** Production deployment

```python
class LiveMyStrategy:
    def __init__(self):
        self.sma_fast = None
        self.sma_slow = None
        self.position = 0
        self.pending_entry_signal = 0  # Signal for NEXT bar

    def process_new_bar(self, open_price, high, low, close, volume, timestamp):
        # Update indicators
        self.update_smas(close)

        # Process pending entry from PREVIOUS bar
        if self.pending_entry_signal != 0:
            self.position = self.pending_entry_signal
            entry_price = open_price  # Execute at current bar's open
            self.pending_entry_signal = 0

        # Generate NEW entry signal for NEXT bar
        if self.sma_fast > self.sma_slow:
            self.pending_entry_signal = 1

        return {'position': self.position, 'entry_price': entry_price}
```

**GOLDEN RULE:** These MUST produce identical signals. Use parity testing.

---

## Sacred Timing Protocol: "Signal on Close, Execute on Next Open"

### Vectorized Pattern
```python
# CORRECT - Uses .shift(1) to prevent look-ahead bias
long_entry = indicator.shift(1) > threshold.shift(1)  # Use PREVIOUS bar

# WRONG - Look-ahead bias (impossible in live trading)
long_entry = indicator > threshold  # Uses CURRENT bar
```

### Stateful Pattern
```python
# CORRECT - Pending signal pattern (gold standard)
if entry_condition:
    self.pending_entry_signal = 1  # Signal detected THIS bar

# Next bar:
if self.pending_entry_signal == 1:
    entry_price = current_open  # Execute at NEXT bar's open
```

---

## File Structure Requirements

### 1. `__init__.py`
```python
from .strategy import MyStrategy

__all__ = ['MyStrategy']
```

### 2. `parameters.py`
```python
DEFAULT_PARAMETERS = {
    "fast_period": 10,
    "slow_period": 30,
    "stop_loss_pct": 2.0
}

PARAMETER_RANGES = {
    "fast_period": (5, 20, 1),      # (min, max, step)
    "slow_period": (20, 50, 1),
    "stop_loss_pct": (1.0, 3.0, 0.5)
}

def validate_parameters(params):
    """Validate parameter constraints."""
    if params['fast_period'] >= params['slow_period']:
        raise ValueError("fast_period must be less than slow_period")
    return True

def get_default_parameters():
    return DEFAULT_PARAMETERS.copy()

def get_parameter_ranges():
    return PARAMETER_RANGES.copy()
```

### 3. `indicators.py`
```python
import vectorbt as vbt

def calculate_moving_average(data, period):
    """Use VectorBT for 7-12x speedup."""
    return vbt.MA.run(data['close'], window=period).ma

def calculate_all_indicators(data, params):
    """Calculate all indicators for strategy."""
    return {
        'fast_ma': calculate_moving_average(data, params['fast_period']),
        'slow_ma': calculate_moving_average(data, params['slow_period'])
    }
```

### 4. `strategy.py`
```python
from ..base import TradingStrategy
from .indicators import calculate_all_indicators
from .parameters import get_default_parameters, get_parameter_ranges, validate_parameters

class MyStrategy(TradingStrategy):
    name = "my_strategy"
    description = "My trading strategy"
    category = "trend_following"
    min_data_points = 100

    def __init__(self):
        super().__init__(self.name)

    def generate_signals(self, data, params, config):
        """Generate trading signals."""
        # Validate
        if not self.validate_parameters(params):
            raise ValueError("Invalid parameters")

        # Calculate indicators
        indicators = calculate_all_indicators(data, params)

        # Generate signals (vectorized)
        signals = pd.Series(0, index=data.index)

        # CRITICAL: Use .shift(1) everywhere
        long_entry = (indicators['fast_ma'].shift(1) >
                     indicators['slow_ma'].shift(1))
        signals[long_entry] = 1

        return signals

    def reset_state(self):
        """Reset state between optimization trials."""
        # Reset any class-level variables here
        pass

    def get_parameter_ranges(self):
        return get_parameter_ranges()

    def validate_parameters(self, params):
        return validate_parameters(params)

    def get_strategy_metadata(self):
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "min_data_points": self.min_data_points
        }
```

### 5. `deployment_template.py`
```python
#!/usr/bin/env python3
"""
Live Trading Strategy Template
"""
from collections import deque

# ==============================================================================
# SECTION 1: PARAMETERS (injected by deployment engine)
# ==============================================================================
fast_period = {fast_period}
slow_period = {slow_period}
stop_loss_pct = {stop_loss_pct}

# MARKET CONFIGURATION
symbol = {symbol}
timeframe = {timeframe}
tick_size = {tick_size}
tick_value = {tick_value}
contracts_per_trade = {contracts_per_trade}

# FENCE:START:SIMULATION
slippage_ticks = {slippage_ticks}
commission_per_trade = {commission_per_trade}
# FENCE:END:SIMULATION

class LiveMyStrategy:
    """Live trading strategy."""

    def __init__(self):
        # Position tracking
        self.position = 0
        self.entry_price = 0.0

        # Data storage (efficient with deque)
        max_lookback = max(fast_period, slow_period) + 5
        self.close_prices = deque(maxlen=max_lookback)

        # Indicator state (EMA)
        self.fast_ma = None
        self.slow_ma = None
        self.fast_alpha = 2.0 / (fast_period + 1)
        self.slow_alpha = 2.0 / (slow_period + 1)

        # Signal state
        self.pending_entry_signal = 0

    def process_new_bar(self, open_price, high, low, close, volume, timestamp):
        """Process new bar of data."""
        # Store data
        self.close_prices.append(close)

        # Update indicators
        if self.fast_ma is None:
            self.fast_ma = close
            self.slow_ma = close
        else:
            self.fast_ma = (close * self.fast_alpha) + (self.fast_ma * (1 - self.fast_alpha))
            self.slow_ma = (close * self.slow_alpha) + (self.slow_ma * (1 - self.slow_alpha))

        # Process pending entry
        if self.pending_entry_signal != 0 and self.position == 0:
            self.position = self.pending_entry_signal
            self.entry_price = open_price
            self.pending_entry_signal = 0

        # Generate new entry signal for NEXT bar
        elif self.position == 0 and len(self.close_prices) >= slow_period:
            if self.fast_ma > self.slow_ma:
                self.pending_entry_signal = 1

        return {
            'position': self.position,
            'entry_price': self.entry_price,
            'fast_ma': self.fast_ma,
            'slow_ma': self.slow_ma
        }

# Strategy instance
strategy = LiveMyStrategy()
```

---

## BaseStrategy Contract (Required Methods)

### Abstract Properties
```python
@property
def name(self) -> str:
    """Strategy identifier for discovery."""
    return "my_strategy"

@property
def description(self) -> str:
    """Human-readable description."""
    return "My trading strategy"

@property
def category(self) -> str:
    """Strategy category."""
    return "trend_following"  # or "mean_reversion", "breakout", etc.

@property
def min_data_points(self) -> int:
    """Minimum data points required."""
    return 100
```

### Abstract Methods
```python
def generate_signals(self, data: pd.DataFrame, params: Dict,
                    config: TradingConfig) -> pd.Series:
    """
    Generate trading signals.

    MUST return pd.Series with:
    - 1 = Long position
    - -1 = Short position
    - 0 = Flat/No position

    MUST use .shift(1) to prevent look-ahead bias.
    """

def reset_state(self) -> None:
    """
    Reset ALL instance variables between optimization trials.

    CRITICAL: Prevents state contamination during optimization.
    """

def get_parameter_ranges(self) -> Dict:
    """
    Return parameter ranges for optimization.

    Format:
    - Numeric: (min, max, step)
    - Categorical: [option1, option2, option3]
    """

def validate_parameters(self, params: Dict) -> bool:
    """
    Validate parameters meet strategy constraints.

    Should check:
    - Required parameters present
    - Values within acceptable ranges
    - Logical constraints
    """

def get_strategy_metadata(self) -> Dict:
    """Return strategy metadata for documentation."""
```

---

## State Management (Critical)

### Option 1: Loop-Local State (Recommended)
```python
def generate_signals(self, data, params, config):
    # State variables inside method - naturally isolated
    position = 0  # ✅ Safe - reset each call
    entry_price = 0.0

    for i in range(1, len(data)):
        # Logic here
        pass
```

### Option 2: Class-Level State (Requires reset_state())
```python
class MyStrategy(TradingStrategy):
    def __init__(self):
        super().__init__(self.name)
        self.position = 0      # ❌ Dangerous without reset_state()

    def generate_signals(self, data, params, config):
        self.position += 1  # Accumulates across trials!
        pass

    def reset_state(self):
        """MANDATORY - Reset ALL class-level state."""
        self.position = 0  # ✅ Must reset every variable
```

**State Contamination Example:**
```python
# Trial 1: self.position = 10 at end
# Trial 2: self.position starts at 10 (contaminated!)
# Trial 3: self.position starts at 20 (contaminated!)

# Result: Invalid optimization, biased results
```

---

## Using VectorBT Indicators (7-2289x Speedup)

### Bollinger Bands
```python
import vectorbt as vbt

def calculate_bollinger_bands(data, length=20, std=2.0):
    bb = vbt.BBANDS.run(data['close'], length=length, num_sd=std)
    return bb.upper, bb.middle, bb.lower  # 7x faster than pandas
```

### Keltner Channels
```python
def calculate_keltner_channels(data, length=20, atr_mult=1.5):
    atr = vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    ma = vbt.MA.run(data['close'], window=length).ma
    upper = ma + (atr * atr_mult)
    lower = ma - (atr * atr_mult)
    return upper, ma, lower  # 12.8x faster
```

### ATR
```python
def calculate_atr(data, length=14):
    return vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    # 9.6x faster than pandas
```

### RSI
```python
def calculate_rsi(data, length=14):
    return vbt.RSI.run(data['close'], window=length).rsi
```

---

## Common Patterns

### Multiple Entry Conditions
```python
# Combine multiple filters
long_entry = (
    (ma_fast.shift(1) > ma_slow.shift(1)) &     # MA crossover
    (rsi.shift(1) < 70) &                       # Not overbought
    (volume.shift(1) > volume_avg.shift(1)) &   # Volume confirmation
    (close.shift(1) > trend_line.shift(1))      # Above trend
)
```

### ATR-Based Stops
```python
# In position management loop
if position == 1:  # Long
    atr_stop = entry_price - (atr[i-1] * params['atr_multiplier'])
    if close[i-1] <= atr_stop:
        position = 0  # Exit
```

### Time-Based Exits
```python
# Track bars in trade
bars_in_trade = 0

if position != 0:
    bars_in_trade += 1
    if bars_in_trade >= params['max_bars_in_trade']:
        position = 0  # Force exit
        bars_in_trade = 0
```

---

## Parity Testing (Mandatory)

Create `tests/test_strategy_parity.py`:

```python
import pytest
import pandas as pd
import numpy as np
from strategies.my_strategy.strategy import MyStrategy
from strategies.my_strategy.deployment_template import LiveMyStrategy

def test_my_strategy_parity():
    """Test vectorized vs stateful implementations."""

    # Create test data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.02)

    test_data = pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.001,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)

    params = {
        'fast_period': 5,
        'slow_period': 20,
        'stop_loss_pct': 2.0
    }

    # Run vectorized
    vectorized = MyStrategy()
    vectorized_signals = vectorized.generate_signals(test_data, params, config)

    # Run stateful
    stateful = LiveMyStrategy()
    stateful_signals = []
    for _, row in test_data.iterrows():
        result = stateful.process_new_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume'], str(row.name)
        )
        stateful_signals.append(result['position'])

    stateful_signals = pd.Series(stateful_signals, index=test_data.index)

    # Assert exact match
    pd.testing.assert_series_equal(vectorized_signals, stateful_signals)
    print("✅ Parity test PASSED")

if __name__ == "__main__":
    test_my_strategy_parity()
```

**Run this test after EVERY strategy change.**

---

## Optimization Best Practices

### Parameter Ranges
```python
# Too narrow - may miss optimal values
"period": (18, 22, 1)  # Only 5 values

# Too wide - wastes computation
"period": (1, 200, 1)  # 200 values (many invalid)

# Just right - focused search
"period": (10, 50, 5)  # 9 values, reasonable range
```

### Using Constraints
```python
def define_constraints(self):
    """Define parameter relationships."""
    return {
        'comparison': [
            ('fast_period', '<', 'slow_period'),   # Logical constraint
            ('stop_loss', '<', 'take_profit')
        ]
    }
# Result: ~50% reduction in optimization time
```

### Trial Count Guidelines
- Simple strategies: 100-500 trials
- Medium complexity: 1,000-5,000 trials
- Production optimization: 5,000-10,000 trials

---

## Critical Pitfalls Checklist

Before deploying:

### Logic Verification
- [ ] Parity test passes (vectorized vs stateful match)
- [ ] No look-ahead bias (all .shift(1) present)
- [ ] Pending signal pattern in stateful version
- [ ] State reset complete (reset_state() clears all vars)

### Parameter Validation
- [ ] Reasonable ranges defined
- [ ] Logical constraints enforced
- [ ] Edge case handling (extreme values)
- [ ] Validation logic comprehensive

### Testing
- [ ] Minimum data check (`min_data_points`)
- [ ] Data validation (missing/invalid data)
- [ ] Edge case data (flat, trending, volatile)
- [ ] Parameter stress test

### Deployment
- [ ] Template placeholders complete (`{parameter}`)
- [ ] Fence integrity (FENCE:START/END:SIMULATION)
- [ ] Self-contained template (no external imports)
- [ ] State initialization in `__init__`

---

## Testing Your Strategy

```bash
# 1. Run parity test
pytest tests/test_strategy_parity.py -v

# 2. Run quick optimization (10 trials)
python TopStepB/main_runner.py \
  --strategy my_strategy \
  --symbol MES \
  --timeframe 1m \
  --max-trials 10

# 3. Check deployed files
ls runs/*/deployed_strategies/

# 4. Validate output
cat runs/*/validation_results.json | jq '.[] | .overall_status'
```

---

## Example: Bollinger Squeeze Strategy

See complete implementation:
- `TopStepB/strategies/bollinger_squeeze/strategy.py` (250 lines)
- `TopStepB/strategies/bollinger_squeeze/indicators.py` (150 lines)
- `TopStepB/strategies/bollinger_squeeze/parameters.py` (100 lines)
- `TopStepB/strategies/bollinger_squeeze/deployment_template.py` (400 lines)

**Reference implementation:** Fully tested, production-ready example.

---

## Summary: Five Pillars

1. **Convention Over Configuration** - Follow 4-file structure
2. **Dual Implementation Parity** - Vectorized and stateful MUST match
3. **Sacred Timing Protocol** - Signal on close, execute on next open
4. **State Isolation** - Reset everything in `reset_state()`
5. **Comprehensive Testing** - Parity tests, validation, edge cases

Follow these pillars for production-ready strategies.

---

**Next Steps:**
- Read `docs/ARCHITECTURE.md` for pipeline details
- Review `TopStepB/strategies/bollinger_squeeze/` for reference
- Create your strategy following this guide
- Run parity tests and optimization
- Deploy and validate

**For full details:** See archived `STRATEGY_DEVELOPMENT_GUIDE.md` and `STRATEGY_REQUIREMENTS_SPECIFICATION.md` in `docs/archive/`
