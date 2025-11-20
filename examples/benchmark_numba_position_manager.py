"""
Standalone benchmark and validation script for Numba Position Manager.
Run this from the project root directory.
"""

import pandas as pd
import numpy as np
import time
import sys

# Set up paths
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from TopStepB.strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
from TopStepB.strategies.bollinger_squeeze.parameters import get_default_parameters
from TopStepB.strategies.bollinger_squeeze.indicators import calculate_all_indicators
from TopStepB.strategies.bollinger_squeeze.numba_position_manager import (
    apply_position_management_wrapper,
    NUMBA_AVAILABLE,
)
from TopStepB.config.system_config import create_trading_config


def generate_test_data(n=1000, seed=42):
    """Generate synthetic OHLCV data for testing with valid OHLC relationships."""
    np.random.seed(seed)

    # Generate base close prices
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)

    # Generate open prices close to close (small variation)
    open_ = close + (np.random.rand(n) - 0.5) * 0.5

    # Generate high and low ensuring valid OHLC relationships
    # high must be >= max(open, close)
    # low must be <= min(open, close)
    high = np.maximum(open_, close) + np.random.rand(n) * 1.5
    low = np.minimum(open_, close) - np.random.rand(n) * 1.5

    volume = np.random.randint(1000, 10000, n)

    df = pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2023-01-01', periods=n, freq='5min'))

    return df


def test_correctness():
    """Test that Numba implementation matches original."""
    print("\n" + "="*70)
    print("CORRECTNESS VALIDATION")
    print("="*70)

    if not NUMBA_AVAILABLE:
        print("\nERROR: Numba not available!")
        return False

    data = generate_test_data(1000)
    params = get_default_parameters()

    # Test all three exit methods
    exit_methods = ['fixed_rr', 'trailing_donchian', 'opposite_band']

    all_passed = True

    for exit_method in exit_methods:
        print(f"\nTesting exit method: {exit_method}")

        params['exit_method'] = exit_method
        indicators = calculate_all_indicators(data, params, use_gpu=None)

        # Create entry signals
        signals = pd.Series(0, index=data.index, dtype=np.int8)
        signals.iloc[100] = 1
        signals.iloc[300] = -1
        signals.iloc[500] = 1

        # Get Numba result
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

        strategy = BollingerSqueezeStrategy()
        numba_result = strategy._apply_stateful_position_management(
            data, signals, indicators, params
        )

        # Get original result
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
        original_result = strategy._apply_stateful_position_management(
            data, signals, indicators, params
        )

        # Restore
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

        # Compare
        if np.array_equal(numba_result.values, original_result.values):
            print(f"  ✓ PASSED - Results match exactly")
        else:
            print(f"  ✗ FAILED - Results differ!")
            diff_count = np.sum(numba_result.values != original_result.values)
            print(f"    Differences: {diff_count}/{len(data)} bars")
            all_passed = False

    return all_passed


def run_performance_benchmarks():
    """Run comprehensive performance benchmarks."""
    print("\n" + "="*70)
    print("PERFORMANCE BENCHMARKS")
    print("="*70)

    if not NUMBA_AVAILABLE:
        print("\nERROR: Numba not available!")
        return

    sizes = [500, 1000, 2000, 5000]
    params = get_default_parameters()
    params['exit_method'] = 'trailing_donchian'

    results = []

    for n in sizes:
        print(f"\nData size: {n} bars")

        # Generate data
        data = generate_test_data(n)
        indicators = calculate_all_indicators(data, params, use_gpu=None)

        # Create entry signals
        signals = pd.Series(0, index=data.index, dtype=np.int8)
        signals.iloc[min(100, n-1)] = 1
        if n > 300:
            signals.iloc[300] = -1
        if n > 500:
            signals.iloc[500] = 1

        strategy = BollingerSqueezeStrategy()
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module

        # Warmup
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True
        for _ in range(3):
            _ = strategy._apply_stateful_position_management(data, signals, indicators, params)

        # Benchmark Numba
        numba_times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
            numba_times.append(time.perf_counter() - start)

        numba_avg = np.mean(numba_times)
        numba_std = np.std(numba_times)

        # Benchmark original
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
        original_times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
            original_times.append(time.perf_counter() - start)

        original_avg = np.mean(original_times)
        original_std = np.std(original_times)

        # Restore
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

        speedup = original_avg / numba_avg

        print(f"  Original: {original_avg*1000:.2f}ms ± {original_std*1000:.2f}ms")
        print(f"  Numba:    {numba_avg*1000:.2f}ms ± {numba_std*1000:.2f}ms")
        print(f"  Speedup:  {speedup:.2f}x")

        results.append({
            'size': n,
            'original_ms': original_avg * 1000,
            'numba_ms': numba_avg * 1000,
            'speedup': speedup,
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n{'Size':<10} {'Original':<15} {'Numba':<15} {'Speedup':<10}")
    print("-" * 50)
    for r in results:
        print(f"{r['size']:<10} {r['original_ms']:<15.2f} {r['numba_ms']:<15.2f} {r['speedup']:<10.2f}x")

    avg_speedup = np.mean([r['speedup'] for r in results])
    print(f"\nAverage speedup: {avg_speedup:.2f}x")

    return results


def test_integration():
    """Test full strategy integration."""
    print("\n" + "="*70)
    print("INTEGRATION TEST")
    print("="*70)

    if not NUMBA_AVAILABLE:
        print("\nERROR: Numba not available!")
        return False

    data = generate_test_data(500)
    params = get_default_parameters()
    config = create_trading_config(
        symbol="ES",
        timeframe="5m",
        account_type="topstep_50k"
    )

    strategy = BollingerSqueezeStrategy()

    try:
        signals = strategy.generate_signals(data, params, config)
        print(f"\n✓ Strategy executed successfully")
        print(f"  Generated {len(signals)} signals")
        print(f"  Long positions: {np.sum(signals == 1)}")
        print(f"  Short positions: {np.sum(signals == -1)}")
        print(f"  Flat: {np.sum(signals == 0)}")
        return True
    except Exception as e:
        print(f"\n✗ Strategy execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests and benchmarks."""
    print("\n" + "="*70)
    print("NUMBA POSITION MANAGER - COMPREHENSIVE TEST SUITE")
    print("="*70)

    if not NUMBA_AVAILABLE:
        print("\nERROR: Numba is not installed!")
        print("Install with: pip install numba")
        return 1

    print(f"\n✓ Numba is available")

    # Run tests
    correctness_passed = test_correctness()

    if not correctness_passed:
        print("\n" + "="*70)
        print("ERROR: Correctness tests failed!")
        print("="*70)
        return 1

    integration_passed = test_integration()

    if not integration_passed:
        print("\n" + "="*70)
        print("ERROR: Integration tests failed!")
        print("="*70)
        return 1

    # Run benchmarks
    results = run_performance_benchmarks()

    # Final summary
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print("\n✓ All correctness tests PASSED")
    print("✓ Integration test PASSED")

    if results:
        avg_speedup = np.mean([r['speedup'] for r in results])
        print(f"\n🚀 Average Performance Improvement: {avg_speedup:.2f}x faster")

        if avg_speedup >= 5.0:
            print("   ⭐ EXCELLENT - Exceeded 5x target!")
        elif avg_speedup >= 3.0:
            print("   ✓ GOOD - Significant speedup achieved")
        elif avg_speedup >= 2.0:
            print("   ⚠ MODERATE - Some speedup achieved")
        else:
            print("   ⚠ WARNING - Speedup below 2x")

    print("\n" + "="*70)
    return 0


if __name__ == '__main__':
    exit(main())
