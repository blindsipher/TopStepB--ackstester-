"""
Isolated benchmark of JUST the position management loop.
This shows the pure speedup without indicator calculation overhead.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import time

from TopStepB.strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
from TopStepB.strategies.bollinger_squeeze.parameters import get_default_parameters
from TopStepB.strategies.bollinger_squeeze.indicators import calculate_all_indicators
import TopStepB.strategies.bollinger_squeeze.strategy as strat_module


def generate_realistic_data(n=2000):
    """Generate realistic OHLCV data."""
    np.random.seed(42)

    returns = np.random.randn(n) * 0.005
    close = 100 * np.exp(np.cumsum(returns))

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
    print("ISOLATED POSITION MANAGEMENT LOOP BENCHMARK")
    print("="*70)

    # Generate test data
    data = generate_realistic_data(2000)
    params = get_default_parameters()

    # Pre-calculate indicators (this is the same for both tests)
    print(f"\nPre-calculating indicators for {len(data)} bars...")
    indicators = calculate_all_indicators(data, params, use_gpu=None)

    # Generate entry signals
    signals = pd.Series(0, index=data.index, dtype=np.int8)
    signals.iloc[100] = 1
    signals.iloc[500] = -1
    signals.iloc[1000] = 1
    signals.iloc[1500] = -1

    strategy = BollingerSqueezeStrategy()

    print(f"Dataset: {len(data)} bars")
    print(f"Exit method: {params['exit_method']}")
    print(f"Entry signals: {np.sum(signals != 0)}")

    # Benchmark JUST the position management loop
    print("\n" + "="*70)
    print("BENCHMARKING POSITION MANAGEMENT LOOP ONLY")
    print("="*70)

    # Numba version
    print("\n[1] Numba JIT-Compiled Version")
    print("-"*70)

    strat_module.USE_NUMBA_POSITION_MANAGEMENT = True
    numba_times = []

    # Warmup
    for _ in range(3):
        _ = strategy._apply_stateful_position_management(data, signals, indicators, params)

    # Benchmark
    for i in range(100):
        start = time.perf_counter()
        _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
        elapsed = time.perf_counter() - start
        numba_times.append(elapsed)

    numba_avg = np.mean(numba_times)
    numba_std = np.std(numba_times)
    numba_min = np.min(numba_times)
    numba_max = np.max(numba_times)

    print(f"Runs:    100")
    print(f"Average: {numba_avg*1000:.4f}ms")
    print(f"Std Dev: {numba_std*1000:.4f}ms")
    print(f"Min:     {numba_min*1000:.4f}ms")
    print(f"Max:     {numba_max*1000:.4f}ms")

    # Python version
    print("\n[2] Original Python Loop Version")
    print("-"*70)

    strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
    python_times = []

    for i in range(100):
        start = time.perf_counter()
        _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
        elapsed = time.perf_counter() - start
        python_times.append(elapsed)

    python_avg = np.mean(python_times)
    python_std = np.std(python_times)
    python_min = np.min(python_times)
    python_max = np.max(python_times)

    print(f"Runs:    100")
    print(f"Average: {python_avg*1000:.4f}ms")
    print(f"Std Dev: {python_std*1000:.4f}ms")
    print(f"Min:     {python_min*1000:.4f}ms")
    print(f"Max:     {python_max*1000:.4f}ms")

    # Restore
    strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

    # Calculate results
    speedup = python_avg / numba_avg
    time_saved = python_avg - numba_avg
    percent_reduction = (time_saved / python_avg) * 100

    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    print(f"\nOriginal Python:     {python_avg*1000:.4f}ms ± {python_std*1000:.4f}ms")
    print(f"Numba Optimized:     {numba_avg*1000:.4f}ms ± {numba_std*1000:.4f}ms")
    print(f"\nTime Saved:          {time_saved*1000:.4f}ms ({percent_reduction:.1f}% reduction)")
    print(f"Speedup Factor:      {speedup:.2f}x")

    if speedup >= 5:
        print(f"\n🎯 TARGET ACHIEVED: {speedup:.2f}x > 5x target")
    else:
        print(f"\n⚠️  Below target: {speedup:.2f}x < 5x target")

    print("\n" + "="*70)
    print("OPTIMIZATION IMPACT")
    print("="*70)

    trials = [100, 1000, 10000, 100000]

    for n_trials in trials:
        total_saved = time_saved * n_trials
        if total_saved < 1:
            print(f"\n{n_trials:,} trials: Save {total_saved*1000:.0f}ms")
        elif total_saved < 60:
            print(f"\n{n_trials:,} trials: Save {total_saved:.2f}s")
        else:
            print(f"\n{n_trials:,} trials: Save {total_saved/60:.2f} minutes")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()
