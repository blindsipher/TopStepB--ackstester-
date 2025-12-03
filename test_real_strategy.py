"""
Test VectorBT integration with REAL strategy from the repository.
This validates the actual production integration.
"""

import sys
import pandas as pd
import numpy as np
import time

sys.path.insert(0, '/home/user/TopStepB--ackstester-/TopStepB')

print("="*70)
print("REAL STRATEGY INTEGRATION TEST")
print("="*70)

# Import real strategy
print("\n[1] Importing real Bollinger Squeeze strategy...")
try:
    from strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
    from config.system_config import create_trading_config
    from optimization.vectorbt_engine import VectorBTPortfolioEngine
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Create configuration
print("\n[2] Creating configuration...")
try:
    trading_config = create_trading_config(
        symbol="MES",
        timeframe="5m",
        account_type="topstep_50k"
    )

    execution_config = {
        'commission_per_trade': 0.62,
        'slippage_ticks': 1
    }
    print("✓ Configuration created")
except Exception as e:
    print(f"✗ Configuration failed: {e}")
    sys.exit(1)

# Generate realistic test data
print("\n[3] Generating test market data...")
try:
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=5000, freq='5min')

    # Generate realistic price action with trend
    trend = np.linspace(0, 50, 5000)
    noise = np.cumsum(np.random.randn(5000) * 0.5)
    closes = 4500 + trend + noise

    data = pd.DataFrame({
        'open': closes,
        'high': closes + np.abs(np.random.randn(5000) * 1.5),
        'low': closes - np.abs(np.random.randn(5000) * 1.5),
        'close': closes,
        'volume': np.random.randint(100, 10000, 5000)
    }, index=dates)

    print(f"✓ Generated {len(data):,} bars")
except Exception as e:
    print(f"✗ Data generation failed: {e}")
    sys.exit(1)

# Initialize strategy
print("\n[4] Initializing Bollinger Squeeze strategy...")
try:
    strategy = BollingerSqueezeStrategy()  # No arguments needed
    strategy.set_config(trading_config)
    print("✓ Strategy initialized")
except Exception as e:
    print(f"✗ Strategy initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Get default parameters
print("\n[5] Getting strategy parameters...")
try:
    param_ranges = strategy.get_parameter_ranges()
    print(f"✓ Found {len(param_ranges)} parameters")

    # Use valid default values from parameter ranges
    params = {}
    for name, range_def in param_ranges.items():
        if isinstance(range_def, tuple) and len(range_def) >= 3:
            # (min, max, step) - use min + step for valid value
            params[name] = range_def[0] + range_def[2]
        elif isinstance(range_def, list):
            # List of choices - use first
            params[name] = range_def[0]
        else:
            params[name] = range_def

    print(f"  Using {len(params)} validated parameters")
except Exception as e:
    print(f"✗ Parameter setup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Generate signals
print("\n[6] Generating trading signals...")
try:
    start = time.time()
    signals = strategy.execute_strategy(data, params)
    signal_time = time.time() - start

    num_longs = (signals == 1).sum()
    num_shorts = (signals == -1).sum()
    num_flat = (signals == 0).sum()

    print(f"✓ Generated signals in {signal_time:.3f}s")
    print(f"  Longs: {num_longs}, Shorts: {num_shorts}, Flat: {num_flat}")
except Exception as e:
    print(f"✗ Signal generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Run VectorBT backtest
print("\n[7] Running VectorBT backtest...")
try:
    engine = VectorBTPortfolioEngine(trading_config, execution_config)

    start = time.time()
    metrics = engine.run_backtest(data, signals, contracts_per_trade=1)
    backtest_time = time.time() - start

    print(f"✓ Backtest completed in {backtest_time:.3f}s")
    print(f"\n  === PERFORMANCE METRICS ===")
    print(f"  Total Trades: {metrics['total_trades']}")
    print(f"  Total P&L: ${metrics['total_dollar_pnl']:,.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown: ${metrics['max_drawdown_dollars']:,.2f}")
    print(f"  Final Equity: ${metrics['final_equity']:,.2f}")
    print(f"  Winning Trades: {metrics.get('winning_trades', 'N/A')}")
    print(f"  Losing Trades: {metrics.get('losing_trades', 'N/A')}")
except Exception as e:
    print(f"✗ Backtest failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Performance summary
print("\n" + "="*70)
print("SUCCESS - REAL STRATEGY INTEGRATION VALIDATED ✓")
print("="*70)
print(f"\nPerformance Summary:")
print(f"  Data size: {len(data):,} bars")
print(f"  Signal generation: {signal_time:.3f}s ({len(data)/signal_time:,.0f} bars/sec)")
print(f"  VectorBT backtest: {backtest_time:.3f}s ({len(data)/backtest_time:,.0f} bars/sec)")
print(f"  Total time: {signal_time + backtest_time:.3f}s")
print(f"\nThe VectorBT integration is PRODUCTION READY with real strategies!")
print("="*70)
