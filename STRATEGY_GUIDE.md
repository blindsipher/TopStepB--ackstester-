# TopStepB Strategy Development Guide
## Create Your Own Optimized Trading Strategies

**Quick Start Guide for Building Optuna-Optimized Python Trading Strategies**

---

## Table of Contents

1. [Quick Start - 5 Minutes](#quick-start---5-minutes)
2. [Strategy Structure](#strategy-structure)
3. [Step-by-Step Tutorial](#step-by-step-tutorial)
4. [Optuna Integration](#optuna-integration)
5. [Performance Optimization](#performance-optimization)
6. [Testing & Validation](#testing--validation)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start - 5 Minutes

### What You Need to Know

TopStepB uses a **convention-based architecture**. Drop a strategy folder into `TopStepB/strategies/`, and the system automatically:
- Discovers your strategy
- Generates parameter combinations (Optuna)
- Runs parallel optimization trials
- Validates results with walk-forward testing
- Deploys optimized parameters

### Minimal Strategy Structure

```
TopStepB/strategies/your_strategy/
├── __init__.py              # Empty file (required for Python package)
├── strategy.py              # Core strategy logic (REQUIRED)
├── parameters.py            # Parameter definitions (REQUIRED)
├── indicators.py            # Technical indicators (optional)
└── deployment_template.py   # Live trading template (optional)
```

### Run Your Strategy

```bash
python main_runner.py --strategy your_strategy --max-trials 100
```

That's it! The system handles everything else.

---

## Strategy Structure

### 1. strategy.py - Core Logic

This file defines **how signals are generated** from indicators and parameters.

**Template:**

```python
"""
your_strategy/strategy.py
"""
import pandas as pd
from typing import Dict, Any

def generate_signals(
    data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> pd.Series:
    """
    Generate trading signals from indicators and parameters.

    Args:
        data: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        indicators: Dictionary of pre-calculated indicators
        params: Dictionary of strategy parameters (from Optuna trial)

    Returns:
        pd.Series: Trading signals
            1 = Long entry
            -1 = Short entry
            0 = Flat/Exit
    """
    # Initialize signals to flat
    signals = pd.Series(0, index=data.index, dtype=int)

    # Example: Moving average crossover
    fast_ma = indicators['fast_ma']
    slow_ma = indicators['slow_ma']

    # CRITICAL: Use .shift(1) to prevent look-ahead bias
    # This ensures we're using PREVIOUS bar's indicator value
    long_condition = (fast_ma > slow_ma.shift(1))
    short_condition = (fast_ma < slow_ma.shift(1))

    signals[long_condition] = 1
    signals[short_condition] = -1

    # Forward-fill signals (maintain position until exit)
    signals = signals.replace(0, pd.NA).ffill().fillna(0).astype(int)

    return signals
```

**Key Rules:**
- ✅ Always use `.shift(1)` for indicator lookback (prevent look-ahead bias)
- ✅ Return pd.Series with 1, -1, 0 signals
- ✅ Index must match `data.index`
- ✅ Forward-fill signals to maintain positions

---

### 2. parameters.py - Optuna Parameter Definitions

This file tells Optuna **what parameters to optimize** and their valid ranges.

**Template:**

```python
"""
your_strategy/parameters.py
"""
from typing import Dict, Any
import optuna

def suggest_parameters(trial: optuna.Trial) -> Dict[str, Any]:
    """
    Define parameter search space for Optuna optimization.

    Args:
        trial: Optuna trial object

    Returns:
        Dictionary of suggested parameters
    """
    params = {
        # Integer parameters
        'fast_ma_period': trial.suggest_int('fast_ma_period', 5, 50, step=5),
        'slow_ma_period': trial.suggest_int('slow_ma_period', 20, 200, step=10),

        # Float parameters
        'profit_target_pct': trial.suggest_float('profit_target_pct', 0.5, 5.0, step=0.5),
        'stop_loss_pct': trial.suggest_float('stop_loss_pct', 0.5, 3.0, step=0.5),

        # Categorical parameters
        'ma_type': trial.suggest_categorical('ma_type', ['SMA', 'EMA']),

        # Boolean parameters (via categorical)
        'use_volume_filter': trial.suggest_categorical('use_volume_filter', [True, False]),
    }

    # Add parameter constraints (reduce search space)
    # Fast MA must be shorter than slow MA
    if params['fast_ma_period'] >= params['slow_ma_period']:
        raise optuna.TrialPruned()  # Skip invalid combinations

    return params
```

**Parameter Types:**

| Type | Method | Example |
|------|--------|---------|
| **Integer** | `suggest_int(name, low, high, step)` | Period lengths (10, 20, 30) |
| **Float** | `suggest_float(name, low, high, step)` | Percentages (1.0, 1.5, 2.0) |
| **Categorical** | `suggest_categorical(name, choices)` | Options ['SMA', 'EMA'] |
| **Log Scale** | `suggest_float(name, low, high, log=True)` | Wide ranges (1e-5 to 1e-2) |

**Best Practices:**
- Use `step` parameter to reduce search space (5, 10, 15 vs 5, 6, 7...)
- Add constraints with `optuna.TrialPruned()` to skip invalid combinations
- Keep parameter count reasonable (5-15 parameters typical)

---

### 3. indicators.py - Technical Indicators

Calculate technical indicators from OHLCV data.

**Template:**

```python
"""
your_strategy/indicators.py
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_all_indicators(
    data: pd.DataFrame,
    params: Dict[str, Any],
    use_gpu: bool = False
) -> Dict[str, pd.Series]:
    """
    Calculate all technical indicators for the strategy.

    Args:
        data: OHLCV DataFrame
        params: Strategy parameters (from Optuna)
        use_gpu: Whether to use GPU acceleration (optional)

    Returns:
        Dictionary of indicator Series
    """
    indicators = {}

    # Example: Simple Moving Averages
    fast_period = params['fast_ma_period']
    slow_period = params['slow_ma_period']

    if params['ma_type'] == 'SMA':
        indicators['fast_ma'] = data['close'].rolling(fast_period).mean()
        indicators['slow_ma'] = data['close'].rolling(slow_period).mean()
    else:  # EMA
        indicators['fast_ma'] = data['close'].ewm(span=fast_period, adjust=False).mean()
        indicators['slow_ma'] = data['close'].ewm(span=slow_period, adjust=False).mean()

    # Example: ATR for position sizing
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift(1)).abs()
    low_close = (data['low'] - data['close'].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    indicators['atr'] = true_range.ewm(span=14, adjust=False).mean()

    # Optional: Volume indicators
    if params.get('use_volume_filter', False):
        indicators['volume_ma'] = data['volume'].rolling(20).mean()
        indicators['volume_ratio'] = data['volume'] / indicators['volume_ma']

    return indicators
```

**Performance Tips:**
- Use vectorized pandas operations (`.rolling()`, `.ewm()`)
- For heavy calculations, use Numba JIT compilation (see `vectorized_indicators.py`)
- Cache expensive calculations when possible

---

### 4. deployment_template.py - Live Trading (Optional)

Stateful implementation for bar-by-bar live trading.

**Template:**

```python
"""
your_strategy/deployment_template.py
"""

class DeployedStrategy:
    """
    Stateful strategy for live trading execution.

    Maintains state between bars and executes trades in real-time.
    """

    def __init__(self, params: dict):
        """Initialize with optimized parameters."""
        self.params = params

        # State variables
        self.position = 0  # Current position: 1 (long), -1 (short), 0 (flat)
        self.entry_price = None
        self.pending_signal = 0

        # Indicator state
        self.fast_ma_values = []
        self.slow_ma_values = []

    def on_bar(self, bar: dict) -> int:
        """
        Process a single bar and return trading signal.

        Args:
            bar: Dictionary with keys ['open', 'high', 'low', 'close', 'volume', 'timestamp']

        Returns:
            Trading signal: 1 (long), -1 (short), 0 (flat)
        """
        # Update indicators
        self.fast_ma_values.append(bar['close'])
        if len(self.fast_ma_values) > self.params['fast_ma_period']:
            self.fast_ma_values.pop(0)

        self.slow_ma_values.append(bar['close'])
        if len(self.slow_ma_values) > self.params['slow_ma_period']:
            self.slow_ma_values.pop(0)

        # Calculate current MA values
        if len(self.fast_ma_values) >= self.params['fast_ma_period']:
            fast_ma = sum(self.fast_ma_values) / len(self.fast_ma_values)
        else:
            return self.position  # Not enough data yet

        if len(self.slow_ma_values) >= self.params['slow_ma_period']:
            slow_ma = sum(self.slow_ma_values) / len(self.slow_ma_values)
        else:
            return self.position

        # Execute pending signal from previous bar
        if self.pending_signal != 0:
            self.position = self.pending_signal
            self.entry_price = bar['open']  # Execute at open
            self.pending_signal = 0

        # Generate new signal for NEXT bar
        if fast_ma > slow_ma and self.position != 1:
            self.pending_signal = 1  # Go long next bar
        elif fast_ma < slow_ma and self.position != -1:
            self.pending_signal = -1  # Go short next bar

        return self.position
```

**Critical Concepts:**
- **Pending Signal Pattern**: Detect condition on bar N, execute on bar N+1
- **State Management**: Track position, indicators, entry prices
- **Bar-by-Bar Processing**: Exactly mirrors live trading execution

---

## Optuna Integration

### How Optuna Works with Your Strategy

1. **Optuna creates a trial** with parameter suggestions from `parameters.py`
2. **System calculates indicators** using `indicators.py` with trial parameters
3. **System generates signals** using `strategy.py` with indicators and parameters
4. **System runs backtest** and calculates performance metrics
5. **Optuna evaluates trial** using composite score (PNL, Sharpe, drawdown, etc.)
6. **Repeat** for N trials, converging on optimal parameters

### Optimization Configuration

The system uses three Optuna presets:

**Aggressive (Default for Financial Markets):**
```bash
python main_runner.py --strategy your_strategy --optuna-preset aggressive --max-trials 100
```
- Faster convergence (20 startup trials vs 50)
- Early pruning (5 warmup steps vs 10)
- Best for: High-dimensional parameter spaces, financial markets

**Balanced:**
```bash
python main_runner.py --strategy your_strategy --optuna-preset balanced --max-trials 100
```
- Moderate exploration
- Best for: General use, unknown optimal regions

**Conservative:**
```bash
python main_runner.py --strategy your_strategy --optuna-preset conservative --max-trials 200
```
- Thorough exploration (75 startup trials)
- Best for: Critical strategies, research

### Custom Optimization Settings

Edit `TopStepB/optimization/config/optuna_config.py`:

```python
@dataclass
class OptimizationConfig:
    tpe_sampler: TPESamplerConfig
    median_pruner: MedianPrunerConfig
    study_direction: str = "maximize"  # or "minimize"
```

---

## Performance Optimization

### Enable Vectorized Backtest (4x Faster)

In `TopStepB/optimization/objective.py`:

```python
# Feature flag (enabled by default)
USE_VECTORIZED_BACKTEST = True
```

This uses Numba-compiled JIT code for 4x speedup (0.12ms per backtest vs 0.5ms).

### Enable Numba Position Management (16x Faster)

In `TopStepB/strategies/your_strategy/strategy.py`:

```python
# Add at top of file
USE_NUMBA_POSITION_MANAGEMENT = True

if USE_NUMBA_POSITION_MANAGEMENT:
    try:
        from .numba_position_manager import apply_position_management_numba
    except ImportError:
        USE_NUMBA_POSITION_MANAGEMENT = False
```

### Regime-Based Filtering (Optional)

Filter optimization to specific market regimes:

```bash
# Optimize only on trending markets
python main_runner.py --strategy your_strategy \
  --use-regime-filter --regime-types trending \
  --max-trials 100

# Optimize on trending + mean-reverting markets
python main_runner.py --strategy your_strategy \
  --use-regime-filter --regime-types trending,mean_reverting \
  --regime-lookback 100 --max-trials 100
```

**Regime Types:**
- `trending` - ADX > 25, directional moves
- `mean_reverting` - Low ADX, range-bound
- `choppy` - High volatility, no clear trend

---

## Testing & Validation

### Run Optimization

```bash
# Basic optimization (100 trials)
python main_runner.py --strategy your_strategy --max-trials 100

# With 4 parallel workers
python main_runner.py --strategy your_strategy --max-trials 100 --max-workers 4

# Full optimization (500 trials)
python main_runner.py --strategy your_strategy --max-trials 500 --max-workers 8
```

### Validate Results

The system automatically performs:
- **Walk-forward validation** (60/20/20 train/validate/test split)
- **Out-of-sample testing** (test data never seen during optimization)
- **Data leakage prevention** (gap days between splits)

### Check Deployed Strategies

Optimized strategies are saved to:
```
~/.topstep_engine/strategy_packages/deployed_strategies/
  optimized_rank_001_score_0.5445_your_strategy.py
  optimized_rank_002_score_0.5351_your_strategy.py
  ...
```

Each file is a standalone strategy with optimized parameters embedded.

---

## Common Patterns

### Pattern 1: Breakout Strategy

```python
# indicators.py
def calculate_all_indicators(data, params, use_gpu=False):
    indicators = {}
    period = params['breakout_period']

    # Donchian Channels
    indicators['upper_band'] = data['high'].rolling(period).max()
    indicators['lower_band'] = data['low'].rolling(period).min()

    return indicators

# strategy.py
def generate_signals(data, indicators, params):
    signals = pd.Series(0, index=data.index, dtype=int)

    # Breakout logic (with .shift(1) to prevent look-ahead)
    long_breakout = data['close'] > indicators['upper_band'].shift(1)
    short_breakout = data['close'] < indicators['lower_band'].shift(1)

    signals[long_breakout] = 1
    signals[short_breakout] = -1

    return signals.replace(0, pd.NA).ffill().fillna(0).astype(int)
```

### Pattern 2: Mean Reversion

```python
# indicators.py
def calculate_all_indicators(data, params, use_gpu=False):
    indicators = {}
    period = params['bb_period']
    std_dev = params['bb_std_dev']

    # Bollinger Bands
    ma = data['close'].ewm(span=period, adjust=False).mean()
    std = data['close'].rolling(period).std()

    indicators['upper_band'] = ma + (std * std_dev)
    indicators['lower_band'] = ma - (std * std_dev)
    indicators['middle_band'] = ma

    return indicators

# strategy.py
def generate_signals(data, indicators, params):
    signals = pd.Series(0, index=data.index, dtype=int)

    # Mean reversion: buy at lower band, sell at upper band
    long_entry = data['close'] < indicators['lower_band'].shift(1)
    short_entry = data['close'] > indicators['upper_band'].shift(1)

    # Exit at middle band
    exit_signal = (
        (data['close'] > indicators['middle_band'].shift(1)) |
        (data['close'] < indicators['middle_band'].shift(1))
    )

    signals[long_entry] = 1
    signals[short_entry] = -1
    signals[exit_signal] = 0

    return signals.replace(0, pd.NA).ffill().fillna(0).astype(int)
```

### Pattern 3: Multi-Indicator Confluence

```python
# strategy.py
def generate_signals(data, indicators, params):
    signals = pd.Series(0, index=data.index, dtype=int)

    # Require multiple conditions (confluence)
    trend_up = indicators['ema_fast'] > indicators['ema_slow'].shift(1)
    momentum_up = indicators['momentum'] > params['momentum_threshold']
    volume_spike = indicators['volume_ratio'] > params['volume_threshold']

    # All conditions must be true
    long_entry = trend_up & momentum_up & volume_spike

    # Inverse for short
    trend_down = indicators['ema_fast'] < indicators['ema_slow'].shift(1)
    momentum_down = indicators['momentum'] < -params['momentum_threshold']

    short_entry = trend_down & momentum_down & volume_spike

    signals[long_entry] = 1
    signals[short_entry] = -1

    return signals.replace(0, pd.NA).ffill().fillna(0).astype(int)
```

---

## Troubleshooting

### Issue: "Strategy not discovered"

**Solution:**
- Ensure `__init__.py` exists in strategy folder
- Check folder naming (lowercase, underscores only)
- Verify strategy.py and parameters.py exist

### Issue: "Invalid signal array"

**Solution:**
- Signals must be pd.Series with dtype=int
- Only values: 1, -1, 0
- Index must match data.index
- Use `.astype(int)` at the end

### Issue: "Look-ahead bias detected"

**Solution:**
- Always use `.shift(1)` on indicators
- Never compare current bar's close to current bar's indicator
- Use pending signal pattern in deployment_template.py

### Issue: "Optimization too slow"

**Solutions:**
1. Enable vectorized backtest (4x faster)
2. Reduce parameter search space (use `step` in suggest_int/float)
3. Add parameter constraints (use `optuna.TrialPruned()`)
4. Increase `--max-workers` for parallel trials
5. Use aggressive preset: `--optuna-preset aggressive`

### Issue: "No profitable trials found"

**Solutions:**
1. Expand parameter search space
2. Increase `--max-trials` (try 500-1000)
3. Check strategy logic for errors
4. Verify indicator calculations
5. Test on different market regimes (use `--use-regime-filter`)

### Issue: "Memory usage too high"

**Solutions:**
1. Reduce `--max-workers`
2. Use smaller datasets
3. Clear indicator cache between trials
4. Check for memory leaks in custom code

---

## Advanced Topics

### Custom Composite Scoring

Edit `TopStepB/optimization/composite_score.py`:

```python
# Adjust metric weights
default_weights = {
    'PropFirmViability': 0.15,
    'Sortino': 0.10,
    'PNL': 0.25,           # Increase for more PNL focus
    'MaxDD': 0.05,         # Increase for more drawdown penalty
    'ProfitFactor': 0.30,
    'WinRate': 0.10,
    'TradeFrequency': 0.05
}
```

### PostgreSQL Distributed Optimization

For multi-machine optimization:

1. Install PostgreSQL (see `docs/README-POSTGRESQL.md`)
2. Configure connection in `TopStepB/optimization/config/optuna_config.py`
3. Run workers on multiple machines with same study name

### GPU Acceleration (Future)

Coming soon: CuPy-accelerated indicators for 5-10x speedup on NVIDIA GPUs.

---

## Example Strategies

See working examples in `TopStepB/strategies/`:

- **bollinger_squeeze** - Volatility compression breakout system
- Add your own strategies here!

---

## Additional Resources

- **Full Documentation**: See `docs/README.md`
- **Architecture Details**: See `docs/architecture/`
- **Performance Guide**: See `docs/optimizations/`
- **Regime Filtering**: See `docs/regime/`
- **Edge Cases**: See `docs/edge-cases/`

---

## Quick Reference Card

```bash
# Create new strategy
mkdir -p TopStepB/strategies/my_strategy
touch TopStepB/strategies/my_strategy/{__init__.py,strategy.py,parameters.py,indicators.py}

# Run optimization
python main_runner.py --strategy my_strategy --max-trials 100 --max-workers 4

# Use aggressive preset
python main_runner.py --strategy my_strategy --optuna-preset aggressive --max-trials 100

# Filter by regime
python main_runner.py --strategy my_strategy --use-regime-filter --regime-types trending

# Check results
ls ~/.topstep_engine/strategy_packages/deployed_strategies/
```

---

## Support

For questions, issues, or contributions, see the main `README.md` and documentation in `docs/`.

**Happy Trading!** 🚀

---

**Version**: 2.0 (Optimized)
**Last Updated**: 2025-11-20
**System**: TopStepB with Numba/Optuna optimization
**Performance**: 31.8 trials/minute, 4x faster backtesting
