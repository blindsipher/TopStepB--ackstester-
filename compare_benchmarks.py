"""
Compare Baseline vs Optimized Benchmark Results

This script loads both benchmark results and displays a side-by-side comparison
showing the performance improvements from the architectural changes.
"""

import json
import sys
from pathlib import Path


def load_benchmark(filename: str) -> dict:
    """Load benchmark results from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)


def format_time(seconds: float) -> str:
    """Format time in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = seconds / 60
        return f"{minutes:.2f}min"


def calculate_speedup(baseline: float, optimized: float) -> tuple:
    """Calculate speedup factor and percentage improvement."""
    if baseline == 0:
        return 0.0, 0.0
    speedup = baseline / optimized
    percent_improvement = ((baseline - optimized) / baseline) * 100
    return speedup, percent_improvement


def main():
    baseline_file = Path("benchmark_baseline.json")
    optimized_file = Path("benchmark_optimized.json")

    if not baseline_file.exists():
        print(f"❌ Baseline benchmark not found: {baseline_file}")
        print(f"   Run: python benchmark_performance.py --mode baseline")
        return 1

    if not optimized_file.exists():
        print(f"❌ Optimized benchmark not found: {optimized_file}")
        print(f"   Run: python benchmark_performance.py --mode optimized")
        return 1

    # Load results
    baseline = load_benchmark(baseline_file)
    optimized = load_benchmark(optimized_file)

    # Extract key metrics
    baseline_summary = baseline['summary']
    optimized_summary = optimized['summary']
    baseline_memory = baseline['memory']
    optimized_memory = optimized['memory']

    print("\n" + "="*100)
    print(" "*30 + "PERFORMANCE COMPARISON REPORT")
    print("="*100)

    print("\n" + "─"*100)
    print(f"{'METRIC':<40} {'BASELINE':<20} {'OPTIMIZED':<20} {'IMPROVEMENT':<20}")
    print("─"*100)

    # Trial times
    baseline_trial = baseline_summary['avg_trial_time']
    optimized_trial = optimized_summary['avg_trial_time']
    speedup, percent = calculate_speedup(baseline_trial, optimized_trial)

    print(f"{'Average Trial Time':<40} {format_time(baseline_trial):<20} {format_time(optimized_trial):<20} {speedup:.2f}x ({percent:+.1f}%)")

    # Fold times
    baseline_fold = baseline_summary['avg_fold_time']
    optimized_fold = optimized_summary['avg_fold_time']
    speedup, percent = calculate_speedup(baseline_fold, optimized_fold)

    print(f"{'Average Fold Time':<40} {format_time(baseline_fold):<20} {format_time(optimized_fold):<20} {speedup:.2f}x ({percent:+.1f}%)")

    # Total time
    baseline_total = baseline_summary['total_time']
    optimized_total = optimized_summary['total_time']
    speedup, percent = calculate_speedup(baseline_total, optimized_total)

    print(f"{'Total Time (10 trials × 3 folds)':<40} {format_time(baseline_total):<20} {format_time(optimized_total):<20} {speedup:.2f}x ({percent:+.1f}%)")

    print("─"*100)

    # Estimated scaling
    print(f"\n{'ESTIMATED SCALING (Extrapolated)':<40}")
    print("─"*100)

    for n_trials in [50, 100, 500, 1000]:
        baseline_est = baseline_trial * n_trials
        optimized_est = optimized_trial * n_trials
        speedup, percent = calculate_speedup(baseline_est, optimized_est)

        print(f"{f'{n_trials} trials × 3 folds':<40} {format_time(baseline_est):<20} {format_time(optimized_est):<20} {speedup:.2f}x ({percent:+.1f}%)")

    print("─"*100)

    # Memory comparison
    print(f"\n{'MEMORY USAGE':<40}")
    print("─"*100)

    baseline_mem_delta = baseline_memory['delta']
    optimized_mem_delta = optimized_memory['delta']
    mem_reduction = baseline_mem_delta - optimized_mem_delta
    mem_percent = (mem_reduction / baseline_mem_delta) * 100 if baseline_mem_delta != 0 else 0

    print(f"{'Memory Delta':<40} {baseline_mem_delta:+.2f} MB{'':>13} {optimized_mem_delta:+.2f} MB{'':>13} {mem_reduction:.2f} MB saved ({mem_percent:+.1f}%)")

    print("─"*100)

    # Architectural improvements summary
    print(f"\n{'ARCHITECTURAL IMPROVEMENTS IMPLEMENTED':<100}")
    print("─"*100)
    print(f"  ✅  1. Precomputed Numpy Data Layer (float32) - eliminates pandas overhead in hot loop")
    print(f"  ✅  2. Minimal Strategy State (__slots__) - reduces per-instance memory overhead")
    print(f"  ✅  3. Tight Backtest Loop - pure numpy, no repeated allocations")
    print(f"  ✅  4. Walk-Forward Index Ranges - zero-copy slicing instead of data duplication")
    print(f"  ✅  5. Vectorized Indicator Calculations - fast EMA, ATR, Bollinger Bands")
    print("─"*100)

    # Key Takeaways
    overall_speedup, overall_percent = calculate_speedup(baseline_trial, optimized_trial)

    print(f"\n{'KEY TAKEAWAYS':<100}")
    print("─"*100)
    print(f"  🚀  Overall Speedup: {overall_speedup:.2f}x faster ({overall_percent:.1f}% improvement)")
    print(f"  💾  Memory Efficiency: {mem_reduction:.1f} MB less memory per run ({abs(mem_percent):.1f}% reduction)")
    print(f"  ⏱️   Time Saved (500 trials): {format_time(baseline_trial * 500 - optimized_trial * 500)}")
    print(f"  📊  Performance Class: ", end="")

    if overall_speedup >= 5.0:
        print("⭐ EXCEPTIONAL (5x+ speedup)")
    elif overall_speedup >= 3.0:
        print("🔥 EXCELLENT (3-5x speedup)")
    elif overall_speedup >= 2.0:
        print("✨ VERY GOOD (2-3x speedup)")
    elif overall_speedup >= 1.5:
        print("👍 GOOD (1.5-2x speedup)")
    else:
        print("📈 IMPROVED (>1x speedup)")

    print("─"*100)

    # Next steps
    print(f"\n{'NEXT STEPS FOR FURTHER OPTIMIZATION':<100}")
    print("─"*100)
    print(f"  1. Add Optuna Pruning - Report intermediate fold scores, prune bad trials early (30-50% trial reduction)")
    print(f"  2. Numba JIT Compilation - Compile hot loop with @njit for 2-3x additional speedup")
    print(f"  3. Parallel Trials - Run multiple trials concurrently with multiprocessing")
    print(f"  4. GPU Acceleration - Move indicator calculations to GPU for large datasets")
    print(f"  5. Cython Extensions - Rewrite critical paths in Cython for maximum performance")
    print("="*100)
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
