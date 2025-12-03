#!/usr/bin/env python3
"""
Detailed Indicator Timing - Component Breakdown
===============================================

Measures each indicator individually to identify bottlenecks.
"""

import time
import pandas as pd
import sys
from pathlib import Path

# Add TopStepB to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "TopStepB"))

from TopStepB.strategies.bollinger_squeeze.indicators import (
    calculate_bollinger_bands,
    calculate_keltner_channels,
    calculate_atr,
    calculate_donchian_channels,
    calculate_momentum_oscillator,
    detect_squeeze,
    calculate_squeeze_duration,
    calculate_volume_ratio
)


def load_mes_data(bars: int = 10000) -> pd.DataFrame:
    """Load real MES data."""
    mes_file = Path(__file__).parent / "data" / "mes-1m_data.csv"
    df = pd.read_csv(mes_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    df.index.name = 'timestamp'
    return df.iloc[:bars]


def time_function(func, name, *args, n_trials=100, **kwargs):
    """Time a function over multiple trials."""
    # Warmup
    for _ in range(5):
        _ = func(*args, **kwargs)

    # Timed runs
    times = []
    for _ in range(n_trials):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    return avg_time, result


def main():
    print("="*80)
    print("DETAILED INDICATOR TIMING - COMPONENT BREAKDOWN")
    print("="*80)

    # Load data
    print("\nLoading 10,000 bars of MES data...")
    data = load_mes_data(10000)
    print(f"✓ Loaded {len(data):,} bars")

    results = {}

    print("\n" + "="*80)
    print("INDIVIDUAL INDICATOR TIMINGS")
    print("="*80)

    # Bollinger Bands
    print("\n1. Bollinger Bands (VectorBT)")
    avg_time, (bb_upper, bb_middle, bb_lower) = time_function(
        calculate_bollinger_bands,
        "BB",
        data['close'], 20, 2.0
    )
    results['bollinger_bands'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Phase 3 claim: 2.21ms (7x speedup)")
    print(f"   Status: {'✅ PASS' if avg_time < 5 else '❌ FAIL'}")

    # ATR
    print("\n2. ATR (VectorBT)")
    avg_time, atr = time_function(
        calculate_atr,
        "ATR",
        data, 14
    )
    results['atr'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Phase 3 claim: 1.63ms (12.8x speedup)")
    print(f"   Status: {'✅ PASS' if avg_time < 5 else '❌ FAIL'}")

    # Keltner Channels
    print("\n3. Keltner Channels (VectorBT)")
    avg_time, (kc_upper, kc_middle, kc_lower) = time_function(
        calculate_keltner_channels,
        "KC",
        data, 20, 2.0
    )
    results['keltner_channels'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Phase 3 claim: 3.23ms (9.6x speedup)")
    print(f"   Status: {'✅ PASS' if avg_time < 10 else '❌ FAIL'}")

    # Donchian Channels (breakout)
    print("\n4. Donchian Channels - Breakout (pandas)")
    avg_time, (dc_upper, dc_lower) = time_function(
        calculate_donchian_channels,
        "DC_breakout",
        data, 20
    )
    results['donchian_breakout'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Status: {'✅ PASS' if avg_time < 20 else '❌ FAIL'}")

    # Donchian Channels (exit)
    print("\n5. Donchian Channels - Exit (pandas)")
    avg_time, (dc_upper, dc_lower) = time_function(
        calculate_donchian_channels,
        "DC_exit",
        data, 10
    )
    results['donchian_exit'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Status: {'✅ PASS' if avg_time < 20 else '❌ FAIL'}")

    # Momentum Oscillator
    print("\n6. Momentum Oscillator (pandas)")
    avg_time, momentum = time_function(
        calculate_momentum_oscillator,
        "Momentum",
        data, 12
    )
    results['momentum'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Status: {'✅ PASS' if avg_time < 50 else '⚠️  MARGINAL' if avg_time < 100 else '❌ FAIL'}")

    # Squeeze Detection
    print("\n7. Squeeze Detection (boolean logic)")
    avg_time, squeeze = time_function(
        detect_squeeze,
        "Squeeze",
        bb_upper, bb_lower, kc_upper, kc_lower
    )
    results['squeeze_detection'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Status: {'✅ PASS' if avg_time < 5 else '❌ FAIL'}")

    # Squeeze Duration
    print("\n8. Squeeze Duration (rolling logic)")
    avg_time, squeeze_duration = time_function(
        calculate_squeeze_duration,
        "Squeeze Duration",
        squeeze
    )
    results['squeeze_duration'] = avg_time
    print(f"   Time: {avg_time:.2f}ms")
    print(f"   Status: {'✅ PASS' if avg_time < 10 else '❌ FAIL'}")

    # Summary
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)

    total_time = sum(results.values())
    print(f"\nTotal indicator calculation time: {total_time:.2f}ms")
    print(f"\nBreakdown:")
    for name, time_ms in sorted(results.items(), key=lambda x: x[1], reverse=True):
        pct = (time_ms / total_time) * 100
        print(f"  {name:25s}: {time_ms:6.2f}ms ({pct:5.1f}%)")

    # Phase 3 Analysis
    print("\n" + "="*80)
    print("PHASE 3 CLAIM VALIDATION")
    print("="*80)
    print(f"\nPhase 3 Report Claims:")
    print(f"  • Bollinger Bands: 2.21ms (7x speedup)")
    print(f"  • ATR: 1.63ms (12.8x speedup)")
    print(f"  • Keltner Channels: 3.23ms (9.6x speedup)")
    print(f"  • Total VectorBT operations: 7.07ms")
    print(f"  • All indicators combined: 50.60ms")

    vectorbt_total = results['bollinger_bands'] + results['atr'] + results['keltner_channels']
    print(f"\nActual Measurements:")
    print(f"  • Bollinger Bands: {results['bollinger_bands']:.2f}ms")
    print(f"  • ATR: {results['atr']:.2f}ms")
    print(f"  • Keltner Channels: {results['keltner_channels']:.2f}ms")
    print(f"  • Total VectorBT operations: {vectorbt_total:.2f}ms")
    print(f"  • All indicators combined: {total_time:.2f}ms")

    # Bottleneck Analysis
    print("\n" + "="*80)
    print("BOTTLENECK ANALYSIS")
    print("="*80)
    bottlenecks = [(name, time_ms) for name, time_ms in results.items() if time_ms > 50]
    if bottlenecks:
        print("\n⚠️  Performance Bottlenecks (>50ms):")
        for name, time_ms in sorted(bottlenecks, key=lambda x: x[1], reverse=True):
            print(f"  • {name}: {time_ms:.2f}ms (needs optimization)")
    else:
        print("\n✅ No major bottlenecks detected (all components <50ms)")

    # Overall Status
    print("\n" + "="*80)
    if total_time < 50:
        print("✅ EXCELLENT: Total time <50ms (Phase 3 target met)")
    elif total_time < 100:
        print("⚠️  MARGINAL: Total time 50-100ms (below target but acceptable)")
    else:
        print("❌ NEEDS WORK: Total time >100ms (significant optimization needed)")
    print("="*80)


if __name__ == '__main__':
    main()
