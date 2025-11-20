"""
Performance Benchmark Script - Before and After Optimization

This script benchmarks the backtest engine with detailed timing metrics:
- Data loading time
- Indicator calculation time
- Strategy execution time per trial
- Walk-forward fold execution time
- Total optimization time
- Memory usage

Usage:
    python benchmark_performance.py --mode baseline
    python benchmark_performance.py --mode optimized
"""

import time
import psutil
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import argparse
import json

# Add project root and TopStepB to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'TopStepB'))

from data.data_loader import load_data_file
from data.data_splitter import walk_forward_splitter
from strategies.bollinger_squeeze.strategy import BollingerSqueezeStrategy
from strategies.bollinger_squeeze.indicators import calculate_all_indicators
from strategies.bollinger_squeeze.parameters import get_parameter_ranges
from config.system_config import create_trading_config

# Optimized engine imports
from optimization.optimized_backtest import (
    PrecomputedData, FoldIndices, calculate_indicators_fast,
    run_backtest_fast, create_walk_forward_folds_fast
)


class BenchmarkTimer:
    """Context manager for timing code blocks."""
    def __init__(self, name: str, results: Dict):
        self.name = name
        self.results = results
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start_time
        if self.name not in self.results:
            self.results[self.name] = []
        self.results[self.name].append(elapsed)
        print(f"  ⏱️  {self.name}: {elapsed:.3f}s")


def get_memory_usage_mb():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def sample_parameters_from_ranges(param_ranges: Dict, seed: int = None) -> Dict[str, Any]:
    """Sample random parameters from parameter ranges."""
    if seed is not None:
        np.random.seed(seed)

    params = {}
    for param_name, param_spec in param_ranges.items():
        if isinstance(param_spec, tuple):
            if len(param_spec) == 3:  # (min, max, step)
                min_val, max_val, step = param_spec
                # Determine if int or float based on step value
                if isinstance(step, int) and isinstance(min_val, int):
                    # Integer parameter
                    values = np.arange(min_val, max_val + 1, step)
                    params[param_name] = int(np.random.choice(values))
                else:
                    # Float parameter - generate valid values
                    n_steps = int(round((max_val - min_val) / step)) + 1
                    values = np.linspace(min_val, max_val, n_steps)
                    # Round to avoid floating point errors
                    decimal_places = len(str(step).split('.')[-1]) if '.' in str(step) else 0
                    params[param_name] = round(float(np.random.choice(values)), decimal_places)
            elif len(param_spec) == 2:  # (min, max) assume float
                min_val, max_val = param_spec
                params[param_name] = np.random.uniform(min_val, max_val)
        elif isinstance(param_spec, list):
            # Convert numpy types to native Python types
            value = np.random.choice(param_spec)
            if isinstance(value, (np.bool_, np.generic)):
                params[param_name] = value.item()
            else:
                params[param_name] = value

    return params


def benchmark_baseline(data_path: str, n_trials: int = 20, n_folds: int = 3) -> Dict[str, Any]:
    """
    Benchmark the CURRENT (baseline) implementation.

    This mimics the actual optimization loop:
    - Load data
    - Create walk-forward folds
    - For each trial:
        - Sample parameters
        - For each fold:
            - Calculate indicators
            - Run strategy
            - Calculate metrics
    """
    print("\n" + "="*80)
    print("BASELINE BENCHMARK - Current Implementation")
    print("="*80)

    results = {
        'timing': {},
        'memory': {},
        'metadata': {
            'n_trials': n_trials,
            'n_folds': n_folds,
            'mode': 'baseline'
        }
    }

    # Memory baseline
    mem_start = get_memory_usage_mb()
    results['memory']['start'] = mem_start
    print(f"\n📊 Starting memory: {mem_start:.2f} MB")

    # 1. Load data
    print(f"\n1️⃣  Loading data from {data_path}...")
    with BenchmarkTimer("data_loading", results['timing']):
        data = load_data_file(data_path)

    print(f"   Loaded {len(data)} rows, {data['datetime'].min()} to {data['datetime'].max()}")
    results['metadata']['data_rows'] = len(data)

    # 2. Create walk-forward folds
    print(f"\n2️⃣  Creating {n_folds} walk-forward folds...")
    with BenchmarkTimer("fold_creation", results['timing']):
        folds = list(walk_forward_splitter(
            data,
            optimize_window_size=1000,
            validate_window_size=500,
            test_window_size=500,
            step_size=500,
            gap_days=1
        ))

    # Limit to n_folds
    folds = folds[:n_folds]
    print(f"   Created {len(folds)} folds")
    results['metadata']['actual_folds'] = len(folds)

    # 3. Get parameter ranges
    strategy = BollingerSqueezeStrategy()
    param_ranges = strategy.get_parameter_ranges()
    config = create_trading_config(symbol="MNQ", timeframe="1min")

    # 4. Run optimization loop
    print(f"\n3️⃣  Running {n_trials} trials × {len(folds)} folds = {n_trials * len(folds)} total runs...")
    print()

    trial_times = []
    fold_times = []

    trials_completed = 0
    trials_attempted = 0

    while trials_completed < n_trials and trials_attempted < n_trials * 3:  # Max 3x attempts
        trial_start = time.perf_counter()
        trials_attempted += 1

        # Sample parameters (this is what Optuna does)
        params = sample_parameters_from_ranges(param_ranges, seed=trials_attempted)

        # Validate parameters before running (skip invalid combinations)
        try:
            if not strategy.validate_parameters(params):
                continue
        except ValueError:
            continue

        print(f"Trial {trials_completed + 1}/{n_trials}")
        trials_completed += 1

        for fold_idx, fold in enumerate(folds):
            fold_start = time.perf_counter()

            # Get validation data for this fold (this is what gets optimized against)
            test_data = fold.validation

            # This is the hot path - what gets executed many times
            with BenchmarkTimer(f"  fold_{fold_idx + 1}_indicators", results['timing']):
                indicators = calculate_all_indicators(test_data, params, use_gpu=None)

            with BenchmarkTimer(f"  fold_{fold_idx + 1}_strategy", results['timing']):
                strategy.reset_state()
                signals = strategy.generate_signals(test_data, params, config)

            fold_elapsed = time.perf_counter() - fold_start
            fold_times.append(fold_elapsed)

            # Print fold summary
            print(f"  Fold {fold_idx + 1}: {fold_elapsed:.3f}s")

        trial_elapsed = time.perf_counter() - trial_start
        trial_times.append(trial_elapsed)
        print(f"  Trial total: {trial_elapsed:.3f}s\n")

    # 5. Summary statistics
    print("\n" + "="*80)
    print("BASELINE RESULTS SUMMARY")
    print("="*80)

    total_time = sum(trial_times)
    avg_trial_time = np.mean(trial_times)
    avg_fold_time = np.mean(fold_times)

    print(f"\n⏱️  Timing Statistics:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average trial time: {avg_trial_time:.3f}s")
    print(f"   Average fold time: {avg_fold_time:.3f}s")
    print(f"   Estimated time for 100 trials: {avg_trial_time * 100:.1f}s ({avg_trial_time * 100 / 60:.1f} min)")
    print(f"   Estimated time for 500 trials: {avg_trial_time * 500:.1f}s ({avg_trial_time * 500 / 60:.1f} min)")

    # Memory stats
    mem_end = get_memory_usage_mb()
    mem_delta = mem_end - mem_start
    results['memory']['end'] = mem_end
    results['memory']['delta'] = mem_delta

    print(f"\n📊 Memory Statistics:")
    print(f"   Start: {mem_start:.2f} MB")
    print(f"   End: {mem_end:.2f} MB")
    print(f"   Delta: {mem_delta:+.2f} MB")

    # Save detailed results
    results['summary'] = {
        'total_time': total_time,
        'avg_trial_time': avg_trial_time,
        'avg_fold_time': avg_fold_time,
        'trial_times': trial_times,
        'fold_times': fold_times
    }

    return results


def benchmark_optimized(data_path: str, n_trials: int = 20, n_folds: int = 3) -> Dict[str, Any]:
    """
    Benchmark the OPTIMIZED implementation with architectural improvements:
    1. Precomputed numpy data (no pandas in hot loop)
    2. Minimal strategy state (__slots__)
    3. Tight backtest loop (data-oriented design)
    4. Walk-forward as index ranges (not copies)
    5. Ready for Optuna pruning
    """
    print("\n" + "="*80)
    print("OPTIMIZED BENCHMARK - Improved Architecture")
    print("="*80)

    results = {
        'timing': {},
        'memory': {},
        'metadata': {
            'n_trials': n_trials,
            'n_folds': n_folds,
            'mode': 'optimized'
        }
    }

    # Memory baseline
    mem_start = get_memory_usage_mb()
    results['memory']['start'] = mem_start
    print(f"\n📊 Starting memory: {mem_start:.2f} MB")

    # 1. Load data (same as baseline)
    print(f"\n1️⃣  Loading data from {data_path}...")
    with BenchmarkTimer("data_loading", results['timing']):
        data_df = load_data_file(data_path)

    print(f"   Loaded {len(data_df)} rows")
    results['metadata']['data_rows'] = len(data_df)

    # 2. Convert to precomputed numpy arrays (NEW!)
    print(f"\n2️⃣  Precomputing numpy arrays (float32)...")
    with BenchmarkTimer("data_precompute", results['timing']):
        precomputed_data = PrecomputedData.from_dataframe(data_df, symbol="MNQ", timeframe="1min")

    print(f"   Converted to numpy: {precomputed_data.n_bars} bars")
    print(f"   Memory per array: ~{precomputed_data.close.nbytes / 1024:.1f} KB")

    # 3. Create walk-forward folds as index ranges (NEW!)
    print(f"\n3️⃣  Creating {n_folds} walk-forward folds (index ranges only)...")
    with BenchmarkTimer("fold_creation_fast", results['timing']):
        folds = create_walk_forward_folds_fast(
            precomputed_data.n_bars,
            opt_window=1000,
            val_window=500,
            test_window=500,
            step_size=500
        )

    folds = folds[:n_folds]
    print(f"   Created {len(folds)} folds (zero-copy slicing)")
    results['metadata']['actual_folds'] = len(folds)

    # 4. Get parameter ranges
    strategy = BollingerSqueezeStrategy()
    param_ranges = strategy.get_parameter_ranges()

    # 5. Run optimization loop with OPTIMIZED ENGINE
    print(f"\n4️⃣  Running {n_trials} trials × {len(folds)} folds = {n_trials * len(folds)} total runs...")
    print(f"   Using: Precomputed data + Fast indicators + Tight loop\n")

    trial_times = []
    fold_times = []
    trials_completed = 0
    trials_attempted = 0

    while trials_completed < n_trials and trials_attempted < n_trials * 3:
        trial_start = time.perf_counter()
        trials_attempted += 1

        # Sample parameters
        params = sample_parameters_from_ranges(param_ranges, seed=trials_attempted)

        # Validate parameters
        try:
            if not strategy.validate_parameters(params):
                continue
        except ValueError:
            continue

        print(f"Trial {trials_completed + 1}/{n_trials}")
        trials_completed += 1

        for fold_idx, fold in enumerate(folds):
            fold_start = time.perf_counter()

            # Get validation data (VIEW, not copy!)
            val_data = fold.get_validation_slice(precomputed_data)

            # OPTIMIZED: Fast indicator calculation (pure numpy)
            with BenchmarkTimer(f"  fold_{fold_idx + 1}_indicators_fast", results['timing']):
                indicators = calculate_indicators_fast(val_data, params)

            # OPTIMIZED: Tight backtest loop (no pandas)
            with BenchmarkTimer(f"  fold_{fold_idx + 1}_strategy_fast", results['timing']):
                signals, metrics = run_backtest_fast(val_data, indicators, params)

            fold_elapsed = time.perf_counter() - fold_start
            fold_times.append(fold_elapsed)

            print(f"  Fold {fold_idx + 1}: {fold_elapsed:.3f}s (trades: {metrics['n_trades']})")

        trial_elapsed = time.perf_counter() - trial_start
        trial_times.append(trial_elapsed)
        print(f"  Trial total: {trial_elapsed:.3f}s\n")

    # 6. Summary statistics
    print("\n" + "="*80)
    print("OPTIMIZED RESULTS SUMMARY")
    print("="*80)

    total_time = sum(trial_times)
    avg_trial_time = np.mean(trial_times)
    avg_fold_time = np.mean(fold_times)

    print(f"\n⏱️  Timing Statistics:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average trial time: {avg_trial_time:.3f}s")
    print(f"   Average fold time: {avg_fold_time:.3f}s")
    print(f"   Estimated time for 100 trials: {avg_trial_time * 100:.1f}s ({avg_trial_time * 100 / 60:.1f} min)")
    print(f"   Estimated time for 500 trials: {avg_trial_time * 500:.1f}s ({avg_trial_time * 500 / 60:.1f} min)")

    # Memory stats
    mem_end = get_memory_usage_mb()
    mem_delta = mem_end - mem_start
    results['memory']['end'] = mem_end
    results['memory']['delta'] = mem_delta

    print(f"\n📊 Memory Statistics:")
    print(f"   Start: {mem_start:.2f} MB")
    print(f"   End: {mem_end:.2f} MB")
    print(f"   Delta: {mem_delta:+.2f} MB")

    # Save detailed results
    results['summary'] = {
        'total_time': total_time,
        'avg_trial_time': avg_trial_time,
        'avg_fold_time': avg_fold_time,
        'trial_times': trial_times,
        'fold_times': fold_times
    }

    return results


def save_benchmark_results(results: Dict, output_file: str):
    """Save benchmark results to JSON file."""
    # Convert numpy types to native Python types
    def convert_types(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(i) for i in obj]
        return obj

    results = convert_types(results)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark backtest performance")
    parser.add_argument('--mode', choices=['baseline', 'optimized'], default='baseline',
                       help='Benchmark mode: baseline (current) or optimized (improved)')
    parser.add_argument('--data', type=str, default='data/MNQ_1Min_merged.parquet',
                       help='Path to data file')
    parser.add_argument('--trials', type=int, default=20,
                       help='Number of trials to run')
    parser.add_argument('--folds', type=int, default=3,
                       help='Number of walk-forward folds')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file for results (default: benchmark_{mode}.json)')

    args = parser.parse_args()

    # Resolve data path
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = Path(__file__).parent / data_path

    if not data_path.exists():
        print(f"❌ Error: Data file not found: {data_path}")
        print(f"\nLooking for data files...")
        # Try to find some data files
        data_dir = Path(__file__).parent / 'data'
        if data_dir.exists():
            parquet_files = list(data_dir.glob('*.parquet'))
            csv_files = list(data_dir.glob('*.csv'))
            if parquet_files or csv_files:
                print(f"\nFound data files:")
                for f in parquet_files + csv_files:
                    print(f"  - {f.relative_to(Path(__file__).parent)}")
                print(f"\nUsage: python {Path(__file__).name} --data <path_to_data>")
        return 1

    # Set output file
    if args.output is None:
        output_file = f"benchmark_{args.mode}.json"
    else:
        output_file = args.output

    # Run benchmark
    if args.mode == 'baseline':
        results = benchmark_baseline(str(data_path), n_trials=args.trials, n_folds=args.folds)
    elif args.mode == 'optimized':
        results = benchmark_optimized(str(data_path), n_trials=args.trials, n_folds=args.folds)
    else:
        print(f"❌ Unknown mode: {args.mode}")
        return 1

    # Save results
    save_benchmark_results(results, output_file)

    print("\n✅ Benchmark complete!\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
