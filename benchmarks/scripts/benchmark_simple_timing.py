#!/usr/bin/env python3
"""
Simple Timing Benchmark - Component Performance Validation
===========================================================

Direct timing measurements without complexity.
Validates Phase 1-3 performance claims.
"""

import time
import pandas as pd
import sys
from pathlib import Path

# Add TopStepB to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "TopStepB"))

from TopStepB.strategies.bollinger_squeeze.indicators import calculate_all_indicators


def load_mes_data(bars: int = 10000) -> pd.DataFrame:
    """Load real MES data."""
    mes_file = Path(__file__).parent / "data" / "mes-1m_data.csv"
    df = pd.read_csv(mes_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    df.index.name = 'timestamp'
    return df.iloc[:bars]


def time_indicator_calculation(data: pd.DataFrame, n_trials: int = 100):
    """Time indicator calculation only."""
    print("\n" + "="*80)
    print("INDICATOR CALCULATION TIMING")
    print("="*80)

    params = {
        'bb_period': 20,
        'bb_std_dev': 2.0,
        'kc_period': 20,
        'kc_atr_multiplier': 2.0,
        'atr_period': 14,
        'momentum_period': 12,
        'breakout_period': 20,
        'exit_donchian_period': 10,
    }

    print(f"Running {n_trials} trials...")

    # Warmup
    for i in range(5):
        _ = calculate_all_indicators(data, params)

    # Timed runs
    times = []
    for i in range(n_trials):
        start = time.perf_counter()
        indicators = calculate_all_indicators(data, params)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"✓ Average: {avg_time:.2f}ms")
    print(f"✓ Min: {min_time:.2f}ms")
    print(f"✓ Max: {max_time:.2f}ms")
    print(f"✓ Indicators: {len(indicators)}")

    # Phase 3 target: <50ms per calculation
    target = 50
    if avg_time < target:
        status = "✅ PASS"
    elif avg_time < target * 2:
        status = "⚠️  MARGINAL"
    else:
        status = "❌ FAIL"

    print(f"\nTarget: <{target}ms")
    print(f"Status: {status}")

    return avg_time


def main():
    print("="*80)
    print("SIMPLE TIMING BENCHMARK - PHASE 3 VALIDATION")
    print("="*80)
    print("\nValidating VectorBT indicator performance:")
    print("  • Phase 3 claim: 9.8x speedup")
    print("  • Phase 3 target: <50ms per calculation")

    # Load data
    print("\n" + "="*80)
    print("LOADING MES DATA")
    print("="*80)
    bars = 10000
    print(f"Loading {bars:,} bars...")
    data = load_mes_data(bars)
    print(f"✓ Loaded {len(data):,} bars")
    print(f"✓ Date range: {data.index[0]} to {data.index[-1]}")
    print(f"✓ Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

    # Time indicator calculation
    avg_time = time_indicator_calculation(data, n_trials=100)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Indicator Calculation: {avg_time:.2f}ms per trial")
    print(f"Throughput: {1000/avg_time:.1f} calculations/second")
    print(f"1000-trial optimization (sequential): {(avg_time * 1000)/1000/60:.1f} minutes")
    print(f"1000-trial optimization (4 workers): {(avg_time * 1000)/1000/60/4:.1f} minutes")
    print("="*80)


if __name__ == '__main__':
    main()
