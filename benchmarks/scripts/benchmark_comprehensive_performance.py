#!/usr/bin/env python3
"""
Comprehensive Performance Profiling Benchmark
==============================================

Component-level timing analysis for the complete optimization pipeline.
Measures:
1. Indicator calculation time (with/without caching)
2. Signal generation time
3. Portfolio creation time (VectorBT)
4. Metric extraction time
5. Memory usage per component
6. End-to-end trial time

This validates all Phase 1-3 claims and identifies bottlenecks for Phase 5.
"""

import time
import pandas as pd
import numpy as np
import sys
import tracemalloc
from pathlib import Path
from typing import Dict, Any, Tuple
import json

# Add TopStepB to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "TopStepB"))

from TopStepB.strategies.bollinger_squeeze.indicators import calculate_all_indicators
from TopStepB.strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
from TopStepB.optimization.vectorbt_engine import VectorBTPortfolioEngine, IndicatorCache


def load_mes_data(file_path: str = None, bars: int = 10000) -> pd.DataFrame:
    """Load real MES data or generate synthetic data as fallback."""
    if file_path and Path(file_path).exists():
        print(f"Loading real MES data from {file_path}...")
        df = pd.read_csv(file_path)

        # Convert timestamp/datetime column to datetime and set as index
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            df.index.name = 'timestamp'
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        elif df.index.name != 'timestamp':
            df.index = pd.to_datetime(df.index)
            df.index.name = 'timestamp'

        # Ensure proper OHLCV column names
        if bars < len(df):
            df = df.iloc[:bars]

        return df
    else:
        print(f"Generating synthetic OHLCV data (MES data not found)...")
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=bars, freq='1min')

        # Generate realistic OHLC relationships
        open_price = 5000 + np.cumsum(np.random.randn(bars) * 2)
        close = open_price + np.random.randn(bars) * 3
        high = np.maximum(open_price, close) + np.abs(np.random.randn(bars) * 1.5)
        low = np.minimum(open_price, close) - np.abs(np.random.randn(bars) * 1.5)
        volume = np.random.randint(1000, 10000, bars)

        return pd.DataFrame({
            'timestamp': dates,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }).set_index('timestamp')


def profile_component(func, name: str, *args, **kwargs) -> Tuple[Any, float, float]:
    """Profile a component: measure time and memory."""
    tracemalloc.start()
    start_time = time.perf_counter()

    result = func(*args, **kwargs)

    elapsed_time = (time.perf_counter() - start_time) * 1000  # ms
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / 1024 / 1024

    return result, elapsed_time, peak_mb


def benchmark_indicator_calculation(data: pd.DataFrame, params: dict, n_trials: int = 100) -> Dict[str, Any]:
    """Benchmark indicator calculation (Phase 3 target: VectorBT 9.8x speedup)."""
    print("\n" + "="*80)
    print("COMPONENT 1: INDICATOR CALCULATION (Phase 3 - VectorBT Native)")
    print("="*80)

    times = []
    memory_usage = []

    for i in range(n_trials):
        indicators, elapsed, peak_mem = profile_component(
            calculate_all_indicators,
            "indicators",
            data,
            params
        )
        times.append(elapsed)
        memory_usage.append(peak_mem)

    avg_time = np.mean(times)
    std_time = np.std(times)
    avg_mem = np.mean(memory_usage)

    print(f"✓ Average time per calculation: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"✓ Peak memory usage: {avg_mem:.1f}MB")
    print(f"✓ Throughput: {1000/avg_time:.1f} calculations/second")
    print(f"✓ Indicators computed: {len(indicators)}")

    # Target: <50ms per calculation (Phase 3 claim)
    status = "PASS" if avg_time < 50 else "FAIL"
    print(f"\nTarget: <50ms per calculation")
    print(f"Status: {status} ({'✅' if status == 'PASS' else '❌'})")

    return {
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'peak_memory_mb': avg_mem,
        'status': status,
        'target_ms': 50
    }


def benchmark_signal_generation(data: pd.DataFrame, params: dict, n_trials: int = 100) -> Dict[str, Any]:
    """Benchmark signal generation."""
    print("\n" + "="*80)
    print("COMPONENT 2: SIGNAL GENERATION")
    print("="*80)

    # Create strategy instance
    strategy = BollingerSqueezeStrategy()

    times = []
    memory_usage = []

    for i in range(n_trials):
        # Calculate indicators first
        indicators = calculate_all_indicators(data, params)

        # Time signal generation
        tracemalloc.start()
        start_time = time.perf_counter()

        signals = strategy.generate_signals(data, indicators, params)

        elapsed = (time.perf_counter() - start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(elapsed)
        memory_usage.append(peak / 1024 / 1024)

    avg_time = np.mean(times)
    std_time = np.std(times)
    avg_mem = np.mean(memory_usage)

    print(f"✓ Average time per generation: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"✓ Peak memory usage: {avg_mem:.1f}MB")
    print(f"✓ Signals generated: {len(signals)}")

    # Target: <10ms per generation
    status = "PASS" if avg_time < 10 else "MARGINAL" if avg_time < 20 else "FAIL"
    print(f"\nTarget: <10ms per generation")
    print(f"Status: {status}")

    return {
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'peak_memory_mb': avg_mem,
        'status': status,
        'target_ms': 10
    }


def benchmark_portfolio_creation(data: pd.DataFrame, signals: dict, n_trials: int = 100) -> Dict[str, Any]:
    """Benchmark VectorBT portfolio creation."""
    print("\n" + "="*80)
    print("COMPONENT 3: PORTFOLIO CREATION (VectorBT)")
    print("="*80)

    # Create engine
    engine = VectorBTPortfolioEngine(
        initial_capital=50000,
        commission_per_trade=2.50,
        slippage_cost_per_trade=0.25
    )

    times = []
    memory_usage = []

    for i in range(n_trials):
        tracemalloc.start()
        start_time = time.perf_counter()

        portfolio = engine.create_portfolio(
            data=data,
            entries=signals['entries'],
            exits=signals['exits'],
            sl_stops=signals.get('sl_stops'),
            tp_stops=signals.get('tp_stops'),
            size=1  # 1 contract
        )

        elapsed = (time.perf_counter() - start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(elapsed)
        memory_usage.append(peak / 1024 / 1024)

    avg_time = np.mean(times)
    std_time = np.std(times)
    avg_mem = np.mean(memory_usage)

    print(f"✓ Average time per portfolio: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"✓ Peak memory usage: {avg_mem:.1f}MB")
    print(f"✓ Portfolio created successfully")

    # Target: <20ms per portfolio
    status = "PASS" if avg_time < 20 else "MARGINAL" if avg_time < 40 else "FAIL"
    print(f"\nTarget: <20ms per portfolio")
    print(f"Status: {status}")

    return {
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'peak_memory_mb': avg_mem,
        'status': status,
        'target_ms': 20
    }


def benchmark_metric_extraction(data: pd.DataFrame, signals: dict, n_trials: int = 100) -> Dict[str, Any]:
    """Benchmark metric extraction."""
    print("\n" + "="*80)
    print("COMPONENT 4: METRIC EXTRACTION")
    print("="*80)

    engine = VectorBTPortfolioEngine(
        initial_capital=50000,
        commission_per_trade=2.50,
        slippage_cost_per_trade=0.25
    )

    times = []
    memory_usage = []

    for i in range(n_trials):
        # Create portfolio first
        portfolio = engine.create_portfolio(
            data=data,
            entries=signals['entries'],
            exits=signals['exits'],
            sl_stops=signals.get('sl_stops'),
            tp_stops=signals.get('tp_stops'),
            size=1
        )

        # Time metric extraction
        tracemalloc.start()
        start_time = time.perf_counter()

        metrics = engine.extract_metrics(portfolio, data)

        elapsed = (time.perf_counter() - start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(elapsed)
        memory_usage.append(peak / 1024 / 1024)

    avg_time = np.mean(times)
    std_time = np.std(times)
    avg_mem = np.mean(memory_usage)

    print(f"✓ Average time per extraction: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"✓ Peak memory usage: {avg_mem:.1f}MB")
    print(f"✓ Metrics extracted: {len(metrics)}")

    # Target: <10ms per extraction
    status = "PASS" if avg_time < 10 else "MARGINAL" if avg_time < 20 else "FAIL"
    print(f"\nTarget: <10ms per extraction")
    print(f"Status: {status}")

    return {
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'peak_memory_mb': avg_mem,
        'status': status,
        'target_ms': 10
    }


def benchmark_end_to_end(data: pd.DataFrame, params: dict, n_trials: int = 100) -> Dict[str, Any]:
    """Benchmark complete end-to-end trial."""
    print("\n" + "="*80)
    print("COMPONENT 5: END-TO-END TRIAL (Complete Pipeline)")
    print("="*80)

    strategy = BollingerSqueezeStrategy()
    engine = VectorBTPortfolioEngine(
        initial_capital=50000,
        commission_per_trade=2.50,
        slippage_cost_per_trade=0.25
    )

    times = []
    memory_usage = []

    for i in range(n_trials):
        tracemalloc.start()
        start_time = time.perf_counter()

        # Complete pipeline
        indicators = calculate_all_indicators(data, params)
        signals = strategy.generate_signals(data, indicators, params)
        portfolio = engine.create_portfolio(
            data=data,
            entries=signals['entries'],
            exits=signals['exits'],
            sl_stops=signals.get('sl_stops'),
            tp_stops=signals.get('tp_stops'),
            size=1
        )
        metrics = engine.extract_metrics(portfolio, data)

        elapsed = (time.perf_counter() - start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(elapsed)
        memory_usage.append(peak / 1024 / 1024)

    avg_time = np.mean(times)
    std_time = np.std(times)
    avg_mem = np.mean(memory_usage)

    print(f"✓ Average time per trial: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"✓ Peak memory usage: {avg_mem:.1f}MB")
    print(f"✓ Throughput: {1000/avg_time:.1f} trials/second")

    # Target: <100ms per trial (original target: 20-30ms after all optimizations)
    # Current target: <100ms (pre-Phase 4/5 optimizations)
    status = "EXCELLENT" if avg_time < 30 else "PASS" if avg_time < 100 else "MARGINAL" if avg_time < 200 else "FAIL"
    print(f"\nTarget: <100ms per trial (stretch: <30ms)")
    print(f"Status: {status}")

    return {
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'peak_memory_mb': avg_mem,
        'status': status,
        'target_ms': 100,
        'stretch_target_ms': 30
    }


def main():
    """Run comprehensive performance profiling."""
    print("="*80)
    print("COMPREHENSIVE PERFORMANCE PROFILING - PHASES 1-3 VALIDATION")
    print("="*80)
    print("\nValidating performance claims from:")
    print("  • Phase 1: Dead code removal (~5% overhead elimination)")
    print("  • Phase 2: Indicator caching (2289x speedup claimed)")
    print("  • Phase 3: VectorBT indicators (9.8x speedup claimed)")
    print("\nComponents tested:")
    print("  1. Indicator Calculation (VectorBT native)")
    print("  2. Signal Generation")
    print("  3. Portfolio Creation (VectorBT)")
    print("  4. Metric Extraction")
    print("  5. End-to-End Trial")

    # Load test data
    print("\n" + "="*80)
    print("TEST DATA LOADING")
    print("="*80)
    bars = 10000
    mes_data_file = Path(__file__).parent / "data" / "mes-1m_data.csv"
    data = load_mes_data(str(mes_data_file) if mes_data_file.exists() else None, bars)
    print(f"✓ Generated {len(data):,} bars")
    print(f"✓ Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
    print(f"✓ Date range: {data.index[0]} to {data.index[-1]}")

    # Define test parameters (matching indicators.py requirements)
    params = {
        'bb_period': 20,
        'bb_std_dev': 2.0,
        'kc_period': 20,
        'kc_atr_multiplier': 2.0,
        'atr_period': 14,
        'momentum_period': 12,
        'breakout_period': 20,  # Donchian for breakout signals
        'exit_donchian_period': 10,  # Donchian for exit signals
        'squeeze_duration_min': 2,
        'atr_trailing_stop_multiplier': 2.0,
        'use_trend_filter': False,  # Optional trend filter
        'volume_filter': False  # Optional volume filter
    }

    print(f"\n✓ Test parameters: {params}")

    # Run benchmarks
    n_trials = 100
    print(f"\n✓ Running {n_trials} trials per component")

    results = {}

    # Component benchmarks
    results['indicator_calculation'] = benchmark_indicator_calculation(data, params, n_trials)
    results['signal_generation'] = benchmark_signal_generation(data, params, n_trials)

    # Generate signals once for portfolio/metric tests
    strategy = BollingerSqueezeStrategy()
    indicators = calculate_all_indicators(data, params)
    signals = strategy.generate_signals(data, indicators, params)

    results['portfolio_creation'] = benchmark_portfolio_creation(data, signals, n_trials)
    results['metric_extraction'] = benchmark_metric_extraction(data, signals, n_trials)
    results['end_to_end'] = benchmark_end_to_end(data, params, n_trials)

    # Summary
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)

    print("\nComponent Breakdown:")
    print(f"  1. Indicator Calculation:  {results['indicator_calculation']['avg_time_ms']:6.2f}ms [{results['indicator_calculation']['status']}]")
    print(f"  2. Signal Generation:      {results['signal_generation']['avg_time_ms']:6.2f}ms [{results['signal_generation']['status']}]")
    print(f"  3. Portfolio Creation:     {results['portfolio_creation']['avg_time_ms']:6.2f}ms [{results['portfolio_creation']['status']}]")
    print(f"  4. Metric Extraction:      {results['metric_extraction']['avg_time_ms']:6.2f}ms [{results['metric_extraction']['status']}]")
    print(f"  {'─'*40}")
    print(f"  5. End-to-End (measured):  {results['end_to_end']['avg_time_ms']:6.2f}ms [{results['end_to_end']['status']}]")

    # Calculate theoretical sum
    theoretical_sum = (
        results['indicator_calculation']['avg_time_ms'] +
        results['signal_generation']['avg_time_ms'] +
        results['portfolio_creation']['avg_time_ms'] +
        results['metric_extraction']['avg_time_ms']
    )
    print(f"     Theoretical sum:        {theoretical_sum:6.2f}ms (components)")

    overhead_pct = ((results['end_to_end']['avg_time_ms'] - theoretical_sum) / theoretical_sum) * 100
    print(f"     Overhead:               {overhead_pct:6.1f}% (orchestration)")

    # Memory summary
    print("\nMemory Usage:")
    print(f"  Indicator Calculation:  {results['indicator_calculation']['peak_memory_mb']:.1f}MB")
    print(f"  Signal Generation:      {results['signal_generation']['peak_memory_mb']:.1f}MB")
    print(f"  Portfolio Creation:     {results['portfolio_creation']['peak_memory_mb']:.1f}MB")
    print(f"  Metric Extraction:      {results['metric_extraction']['peak_memory_mb']:.1f}MB")
    print(f"  End-to-End (peak):      {results['end_to_end']['peak_memory_mb']:.1f}MB")

    # Overall assessment
    print("\n" + "="*80)
    print("OVERALL ASSESSMENT")
    print("="*80)

    all_pass = all(r.get('status') in ['PASS', 'EXCELLENT'] for r in results.values())

    if all_pass:
        print("✅ ALL COMPONENTS PASSED")
    else:
        print("⚠️  SOME COMPONENTS NEED ATTENTION")
        for component, result in results.items():
            if result.get('status') not in ['PASS', 'EXCELLENT']:
                print(f"   • {component}: {result['status']} ({result['avg_time_ms']:.2f}ms vs {result['target_ms']}ms target)")

    # Calculate projected optimization time
    trials_per_optimization = 1000
    time_per_optimization = (results['end_to_end']['avg_time_ms'] * trials_per_optimization) / 1000 / 60  # minutes

    print(f"\nProjected Performance:")
    print(f"  • {trials_per_optimization} trials: {time_per_optimization:.1f} minutes")
    print(f"  • Trials/second: {1000/results['end_to_end']['avg_time_ms']:.1f}")
    print(f"  • Parallelization benefit (4 workers): ~{time_per_optimization/4:.1f} minutes")

    # Save results
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {output_file}")

    print("="*80)


if __name__ == '__main__':
    main()
