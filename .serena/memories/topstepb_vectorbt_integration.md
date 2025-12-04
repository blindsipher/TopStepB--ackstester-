# TopStepB VectorBT Integration

## VectorBT Usage Locations

### 1. VectorBT Portfolio Engine
**File**: `TopStepB/optimization/vectorbt_engine.py`

**Class**: `VectorBTPortfolioEngine`

**Purpose**: High-performance backtesting with 10-100x speedup vs loop-based methods

**Initialization**:
```python
engine = VectorBTPortfolioEngine(
    trading_config=trading_config,  # Market specs (tick_size, tick_value)
    execution_config={'commission_per_trade': 0.0, 'slippage_ticks': 0}
)
```

**Core Method**: `run_backtest(data, signals, contracts_per_trade)`

```python
portfolio = vbt.Portfolio.from_signals(
    close=data['open'],  # Execute at OPEN (signals pre-shifted)
    entries=entries,
    exits=exits,
    short_entries=short_entries,
    size=contracts_per_trade,
    size_type='amount',
    fixed_fees=total_fees_per_trade,  # Commission + slippage
    freq='1min',  # Data frequency
    init_cash=50000.0,  # TopStep starting capital
    cash_sharing=False,
    sl_stop=np.inf,  # No auto stop-loss
    tp_stop=np.inf   # No auto take-profit
)
```

**Signal Conversion**:
```python
def _signals_to_entries_exits(signals: pd.Series):
    # Convert position signals (1=long, -1=short, 0=flat) to VectorBT boolean arrays
    entries = (signals == 1) & (signals.shift(1).fillna(0) != 1)
    short_entries = (signals == -1) & (signals.shift(1).fillna(0) != -1)
    exits = (signals == 0) & (signals.shift(1).fillna(0) != 0)
    return entries, exits, short_entries
```

**Output**: Metrics dict with:
- `total_dollar_pnl`, `max_drawdown_dollars`, `max_drawdown_percentage`
- `win_rate`, `profit_factor`, `sortino_ratio`, `sharpe_ratio`
- `total_trades`, `winning_trades`, `losing_trades`
- `equity_curve`, `daily_pnl_series`

### 2. VectorBT Validator
**File**: `TopStepB/optimization/vectorbt_validator.py`

**Class**: `VectorBTValidator`

**Purpose**: Extract metrics from VectorBT portfolio objects

**Usage**:
```python
validator = VectorBTValidator(portfolio, strategy_name="backtest")
metrics = validator.get_composite_score_metrics(initial_cash=50000.0)
```

**Extracted Metrics**:
- `portfolio.stats()` - VectorBT standard statistics
- `portfolio.trades.pnl` - Trade-level P&L
- Custom calculations for TopStep compliance

### 3. IndicatorCache System
**File**: `TopStepB/optimization/vectorbt_engine.py`

**Class**: `IndicatorCache`

**Purpose**: Compute indicators ONCE before optimization, reuse across 1000s of trials

**Performance Gain**: 100-500x speedup for indicator-heavy strategies

**Usage Pattern**:
```python
# Pre-optimization setup
cache = IndicatorCache(data)
cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
cache.add_indicator('ema_50', lambda df: df['close'].ewm(span=50).mean())
cache.add_indicator('rsi_14', lambda df: calculate_rsi(df['close'], 14))

# Inside Optuna objective (called 1000s of times)
def objective(trial):
    period = trial.suggest_int('period', 10, 50)
    
    # Cache hit - instant retrieval (no recomputation)
    sma = cache.get('sma_20')
    ema = cache.get('ema_50')
    rsi = cache.get('rsi_14')
    
    # Generate signals using cached indicators
    signals = generate_signals(sma, ema, rsi, period)
    
    # VectorBT backtest (vectorized - fast)
    metrics = engine.run_backtest(data, signals, contracts_per_trade=1)
    return metrics['composite_score']
```

**Methods**:
- `add_indicator(name, compute_func)` - Compute and cache indicator
- `get(name)` - Retrieve cached indicator (O(1) lookup)
- `clear()` - Clear cache and free memory
- `get_stats()` - Cache statistics (hit counts, memory usage)

**Memory Management**:
```python
cache.get_stats()
# {'cached_indicators': 15, 'total_hits': 5000, 'memory_usage_mb': 25.3}
```

### 4. Integration with Optimization Objective
**File**: `TopStepB/optimization/objective.py`

**Pattern**:
```python
class ObjectiveFactory:
    def create_objective(self, strategy_instance, authorized_accesses, ...):
        # Setup IndicatorCache with train data
        cache = IndicatorCache(train_data)
        
        # Pre-compute strategy indicators
        strategy_instance.precompute_indicators(cache)
        
        def objective(trial):
            # Sample parameters
            params = {
                'param1': trial.suggest_int('param1', 10, 50),
                'param2': trial.suggest_float('param2', 0.1, 1.0)
            }
            
            # Strategy generates signals using cached indicators
            signals = strategy_instance.generate_signals(cache, params)
            
            # VectorBT backtests signals (vectorized)
            vectorbt_engine = VectorBTPortfolioEngine(trading_config, execution_config)
            metrics = vectorbt_engine.run_backtest(train_data, signals, contracts_per_trade=1)
            
            # Composite scoring
            score = compute_composite_score(metrics)
            return score
        
        return objective
```

## Performance Benefits

### Without VectorBT (Loop-based)
- **1 trial**: ~500-1000ms
- **1000 trials**: ~8-16 minutes
- **Bottleneck**: Python for-loops iterating bar-by-bar

### With VectorBT (Vectorized)
- **1 trial**: ~10-50ms (10-100x faster)
- **1000 trials**: ~10-50 seconds (10-20x faster end-to-end)
- **Speedup**: NumPy/Pandas vectorized operations

### With VectorBT + IndicatorCache
- **1 trial**: ~5-10ms (100-500x faster for indicator-heavy strategies)
- **1000 trials**: ~5-10 seconds (50-100x faster end-to-end)
- **Speedup**: Indicator computation eliminated (90% of trial time)

## VectorBT-Specific Configurations

**Frequency Mapping**:
```python
freq_map = {
    '1m': '1min', '5m': '5min', '15m': '15min',
    '1h': '1h', '4h': '4h', '1d': '1D'
}
```

**Execution at Open**: Signals pre-shifted for next-bar execution, VectorBT uses `data['open']` for fills

**No Look-Ahead Bias**: Signals must be shifted before calling `run_backtest()`

**Futures P&L**: Tick-based calculation using `tick_size` and `tick_value` from TradingConfig