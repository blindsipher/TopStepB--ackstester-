"""
Real-world demonstration of Numba speedup in strategy execution.
Shows impact on actual signal generation timing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import time

from TopStepB.strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
from TopStepB.strategies.bollinger_squeeze.parameters import get_default_parameters
from TopStepB.config.system_config import create_trading_config
import TopStepB.strategies.bollinger_squeeze.strategy as strat_module


def generate_realistic_data(n=2000):
    """Generate realistic OHLCV data."""
    np.random.seed(42)

    # Random walk with volatility clustering
    returns = np.random.randn(n) * 0.005
    close = 100 * np.exp(np.cumsum(returns))

    # Generate valid OHLC
    open_ = close + (np.random.rand(n) - 0.5) * 0.1
    high = np.maximum(open_, close) + np.random.rand(n) * 0.5
    low = np.minimum(open_, close) - np.random.rand(n) * 0.5
    volume = np.random.randint(5000, 50000, n)

    df = pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2023-01-01', periods=n, freq='5min'))

    return df


def main():
    print("\n" + "="*70)
    print("REAL-WORLD STRATEGY EXECUTION SPEEDUP DEMONSTRATION")
    print("="*70)

    # Generate test data
    data = generate_realistic_data(2000)
    params = get_default_parameters()
    config = create_trading_config(symbol="ES", timeframe="5m")

    strategy = BollingerSqueezeStrategy()

    print(f"\nDataset: {len(data)} bars of 5-minute ES futures data")
    print(f"Exit method: {params['exit_method']}")

    # Warmup
    _ = strategy.generate_signals(data, params, config)

    # Test with Numba ENABLED
    print("\n" + "-"*70)
    print("TESTING WITH NUMBA ENABLED")
    print("-"*70)

    strat_module.USE_NUMBA_POSITION_MANAGEMENT = True
    numba_times = []

    for i in range(5):
        strategy.reset_state()
        start = time.perf_counter()
        signals = strategy.generate_signals(data, params, config)
        elapsed = time.perf_counter() - start
        numba_times.append(elapsed)
        print(f"Run {i+1}: {elapsed*1000:.2f}ms")

    numba_avg = np.mean(numba_times)

    # Test with Numba DISABLED
    print("\n" + "-"*70)
    print("TESTING WITH NUMBA DISABLED (Python fallback)")
    print("-"*70)

    strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
    python_times = []

    for i in range(5):
        strategy.reset_state()
        start = time.perf_counter()
        signals = strategy.generate_signals(data, params, config)
        elapsed = time.perf_counter() - start
        python_times.append(elapsed)
        print(f"Run {i+1}: {elapsed*1000:.2f}ms")

    python_avg = np.mean(python_times)

    # Restore
    strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

    # Results
    speedup = python_avg / numba_avg
    time_saved = python_avg - numba_avg

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    print(f"\nPython (original):  {python_avg*1000:.2f}ms")
    print(f"Numba (optimized):  {numba_avg*1000:.2f}ms")
    print(f"Time saved:         {time_saved*1000:.2f}ms")
    print(f"Speedup:            {speedup:.2f}x faster")

    print("\n" + "="*70)
    print("REAL-WORLD IMPACT")
    print("="*70)

    # Calculate impact for optimization runs
    trials_1k = 1000
    trials_10k = 10000

    print(f"\nFor {trials_1k} optimization trials:")
    print(f"  Python total:  {python_avg * trials_1k:.2f}s")
    print(f"  Numba total:   {numba_avg * trials_1k:.2f}s")
    print(f"  Time saved:    {time_saved * trials_1k:.2f}s")

    print(f"\nFor {trials_10k} optimization trials:")
    print(f"  Python total:  {python_avg * trials_10k / 60:.2f} minutes")
    print(f"  Numba total:   {numba_avg * trials_10k / 60:.2f} minutes")
    print(f"  Time saved:    {time_saved * trials_10k / 60:.2f} minutes")

    if speedup >= 5:
        print("\n✅ SUCCESS: Achieved target speedup!")
    else:
        print(f"\n⚠️  Note: Speedup is {speedup:.2f}x (target was 5x)")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()
