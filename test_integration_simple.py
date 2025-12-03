"""
Simple end-to-end validation test for VectorBT integration.
Tests the actual integration without heavy dependencies.
"""

import sys
import pandas as pd
import numpy as np
from decimal import Decimal

# Add TopStepB to path
sys.path.insert(0, '/home/user/TopStepB--ackstester-/TopStepB')

print("="*70)
print("VECTORBT INTEGRATION - END-TO-END VALIDATION TEST")
print("="*70)

# Test 1: Import all components
print("\n[Test 1] Importing components...")
try:
    from optimization.vectorbt_engine import VectorBTPortfolioEngine, IndicatorCache
    from optimization.strategy_schema import StrategySchema, ParameterDef, ParameterType
    from optimization.performance_monitor import PerformanceMonitor
    from config.system_config import MarketSpec, TradingConfig
    from strategies.base import BaseStrategy
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Create market configuration
print("\n[Test 2] Creating market configuration...")
try:
    from config.system_config import create_trading_config

    # Use factory function to create complete config
    trading_config = create_trading_config(
        symbol="MES",
        timeframe="5m",
        account_type="topstep_50k"
    )

    execution_config = {
        'commission_per_trade': 0.62,
        'slippage_ticks': 1
    }
    print("✓ Configuration created successfully")
except Exception as e:
    print(f"✗ Configuration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Generate test data
print("\n[Test 3] Generating test data...")
try:
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='5min')
    closes = 4500 + np.cumsum(np.random.randn(1000) * 0.5)

    data = pd.DataFrame({
        'open': closes,
        'high': closes + 1,
        'low': closes - 1,
        'close': closes,
        'volume': np.random.randint(100, 1000, 1000)
    }, index=dates)

    print(f"✓ Generated {len(data):,} bars of test data")
except Exception as e:
    print(f"✗ Data generation failed: {e}")
    sys.exit(1)

# Test 4: Create and test simple strategy
print("\n[Test 4] Creating simple test strategy...")
try:
    class SimpleTestStrategy(BaseStrategy):
        @property
        def name(self):
            return "simple_test"

        @property
        def description(self):
            return "Simple test strategy"

        @property
        def category(self):
            return "test"

        @property
        def min_data_points(self):
            return 50

        def generate_signals(self, data, params, config):
            sma = data['close'].rolling(params.get('period', 20)).mean()
            signals = pd.Series(0, index=data.index)
            signals[data['close'] > sma] = 1
            return signals.shift(1).fillna(0)

        def reset_state(self):
            pass

        def get_parameter_ranges(self):
            return {'period': (10, 50, 1)}

        def validate_parameters(self, params):
            return True

        def get_strategy_metadata(self):
            return {'name': self.name}

    strategy = SimpleTestStrategy(name="simple_test")
    strategy.set_config(trading_config)
    print("✓ Strategy created successfully")
except Exception as e:
    print(f"✗ Strategy creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Generate signals
print("\n[Test 5] Generating trading signals...")
try:
    params = {'period': 20}
    signals = strategy.execute_strategy(data, params)

    num_longs = (signals == 1).sum()
    num_shorts = (signals == -1).sum()
    num_flat = (signals == 0).sum()

    print(f"✓ Generated signals: {num_longs} longs, {num_shorts} shorts, {num_flat} flat")
except Exception as e:
    print(f"✗ Signal generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Run VectorBT backtest
print("\n[Test 6] Running VectorBT backtest...")
try:
    engine = VectorBTPortfolioEngine(trading_config, execution_config)

    import time
    start_time = time.time()
    metrics = engine.run_backtest(data, signals, contracts_per_trade=1)
    elapsed_time = time.time() - start_time

    print(f"✓ Backtest completed in {elapsed_time:.3f}s")
    print(f"  Total trades: {metrics['total_trades']}")
    print(f"  Total P&L: ${metrics['total_dollar_pnl']:.2f}")
    print(f"  Win rate: {metrics['win_rate']:.1f}%")
    print(f"  Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Profit factor: {metrics['profit_factor']:.2f}")
    print(f"  Max drawdown: ${metrics['max_drawdown_dollars']:.2f}")
    print(f"  Final equity: ${metrics['final_equity']:.2f}")
except Exception as e:
    print(f"✗ Backtest failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test indicator caching
print("\n[Test 7] Testing indicator caching...")
try:
    cache = IndicatorCache(data)

    # Add indicators
    cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
    cache.add_indicator('sma_50', lambda df: df['close'].rolling(50).mean())

    # Retrieve multiple times
    for _ in range(10):
        sma = cache.get('sma_20')

    stats = cache.get_stats()
    print(f"✓ Indicator caching works")
    print(f"  Cached indicators: {stats['cached_indicators']}")
    print(f"  Total cache hits: {stats['total_hits']}")
except Exception as e:
    print(f"✗ Indicator caching failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Test strategy schema
print("\n[Test 8] Testing strategy schema...")
try:
    schema = StrategySchema(
        strategy_name="test_strategy",
        strategy_class="TestStrategy",
        description="Test",
        category="test"
    )

    schema.add_parameter(ParameterDef(
        name="period",
        param_type=ParameterType.INT,
        default=20,
        min_value=10,
        max_value=50
    ))

    # Test JSON export
    json_str = schema.to_json()

    print(f"✓ Strategy schema works")
    print(f"  Parameters: {len(schema.parameters)}")
except Exception as e:
    print(f"✗ Strategy schema failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Test performance monitoring
print("\n[Test 9] Testing performance monitoring...")
try:
    monitor = PerformanceMonitor()

    with monitor.track('test_operation'):
        # Simulate some work
        _ = data['close'].rolling(50).mean()

    summary = monitor.get_summary()

    print(f"✓ Performance monitoring works")
    print(f"  Tracked operations: {len(summary)}")
except Exception as e:
    print(f"✗ Performance monitoring failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 10: Validate metrics format
print("\n[Test 10] Validating metrics format...")
try:
    required_metrics = [
        'total_dollar_pnl', 'total_return_percentage', 'sharpe_ratio',
        'profit_factor', 'win_rate', 'total_trades', 'max_drawdown_dollars',
        'total_commission_cost', 'total_slippage_cost', 'equity_curve',
        'daily_pnl', 'final_equity'
    ]

    missing = [m for m in required_metrics if m not in metrics]

    if missing:
        print(f"✗ Missing metrics: {missing}")
        sys.exit(1)

    print(f"✓ All required metrics present")
    print(f"  Total metrics: {len(metrics)}")
except Exception as e:
    print(f"✗ Metrics validation failed: {e}")
    sys.exit(1)

# Final summary
print("\n" + "="*70)
print("ALL TESTS PASSED ✓")
print("="*70)
print("\nVectorBT integration is fully functional and tested:")
print("  ✓ All components import correctly")
print("  ✓ Configuration works")
print("  ✓ Data generation works")
print("  ✓ Strategy execution works")
print("  ✓ VectorBT backtesting works")
print("  ✓ Indicator caching works")
print("  ✓ Strategy schema works")
print("  ✓ Performance monitoring works")
print("  ✓ Metrics format validated")
print("\n" + "="*70)
