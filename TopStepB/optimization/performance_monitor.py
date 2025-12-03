"""
Performance Monitoring and Optimization Utilities
=================================================

Tools for monitoring and optimizing backtesting performance with VectorBT.

Features:
- Execution time tracking
- Memory usage monitoring
- Throughput analysis
- Optimization recommendations
- Comparative benchmarks (VectorBT vs loop-based)
"""

import gc
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil

from utils.logger import get_logger

logger = get_logger("performance_monitor")


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    execution_time_seconds: float
    memory_mb: float
    bars_per_second: float
    total_bars: int
    total_trades: int
    engine_type: str  # 'vectorbt' or 'loop'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'execution_time_seconds': self.execution_time_seconds,
            'memory_mb': self.memory_mb,
            'bars_per_second': self.bars_per_second,
            'total_bars': self.total_bars,
            'total_trades': self.total_trades,
            'engine_type': self.engine_type,
            'speedup_vs_baseline': None  # Set by comparison
        }


class PerformanceMonitor:
    """
    Monitor and track backtest performance.

    Usage:
        monitor = PerformanceMonitor()

        with monitor.track('backtest_run'):
            # Run backtest
            metrics = engine.run_backtest(data, signals)

        print(monitor.get_summary())
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.measurements: Dict[str, List[float]] = {}
        self.current_measurement: Optional[str] = None
        self.start_time: Optional[float] = None
        self.start_memory: Optional[float] = None

    @contextmanager
    def track(self, name: str):
        """
        Context manager for tracking execution time and memory.

        Args:
            name: Name for this measurement

        Example:
            with monitor.track('optimization_run'):
                # Code to measure
                pass
        """
        if name not in self.measurements:
            self.measurements[name] = []

        # Record start state
        gc.collect()  # Clean memory before measurement
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB

        try:
            yield
        finally:
            # Record end state
            elapsed_time = time.time() - start_time
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = end_memory - start_memory

            # Store measurement
            self.measurements[name].append({
                'elapsed_time': elapsed_time,
                'memory_mb': memory_used,
                'timestamp': time.time()
            })

            logger.debug(f"{name}: {elapsed_time:.3f}s, {memory_used:.1f}MB")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all measurements.

        Returns:
            Dict with statistics for each tracked operation
        """
        summary = {}

        for name, measurements in self.measurements.items():
            times = [m['elapsed_time'] for m in measurements]
            memory = [m['memory_mb'] for m in measurements]

            summary[name] = {
                'count': len(measurements),
                'total_time': sum(times),
                'avg_time': np.mean(times),
                'min_time': np.min(times),
                'max_time': np.max(times),
                'std_time': np.std(times),
                'avg_memory_mb': np.mean(memory),
                'max_memory_mb': np.max(memory)
            }

        return summary

    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()

        print("\n" + "="*70)
        print("PERFORMANCE SUMMARY")
        print("="*70)

        for name, stats in summary.items():
            print(f"\n{name}:")
            print(f"  Count: {stats['count']}")
            print(f"  Total time: {stats['total_time']:.3f}s")
            print(f"  Avg time: {stats['avg_time']:.3f}s ± {stats['std_time']:.3f}s")
            print(f"  Min/Max time: {stats['min_time']:.3f}s / {stats['max_time']:.3f}s")
            print(f"  Avg memory: {stats['avg_memory_mb']:.1f}MB")

        print("="*70 + "\n")

    def clear(self):
        """Clear all measurements."""
        self.measurements.clear()


class PerformanceComparator:
    """
    Compare performance between VectorBT and loop-based implementations.

    Usage:
        comparator = PerformanceComparator()
        results = comparator.run_comparison(data, signals, config)
        comparator.print_comparison(results)
    """

    def measure_backtest_performance(
        self,
        engine_fn: callable,
        data: pd.DataFrame,
        signals: pd.Series,
        engine_type: str
    ) -> PerformanceMetrics:
        """
        Measure performance of a single backtest run.

        Args:
            engine_fn: Function that runs the backtest
            data: OHLCV data
            signals: Trading signals
            engine_type: 'vectorbt' or 'loop'

        Returns:
            PerformanceMetrics object
        """
        gc.collect()

        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()

        # Run backtest
        metrics = engine_fn(data, signals)

        elapsed_time = time.time() - start_time
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = end_memory - start_memory

        # Calculate throughput
        bars_per_second = len(data) / elapsed_time if elapsed_time > 0 else 0

        return PerformanceMetrics(
            execution_time_seconds=elapsed_time,
            memory_mb=memory_used,
            bars_per_second=bars_per_second,
            total_bars=len(data),
            total_trades=metrics.get('total_trades', 0),
            engine_type=engine_type
        )

    def run_comparison(
        self,
        vectorbt_fn: callable,
        loop_fn: callable,
        data: pd.DataFrame,
        signals: pd.Series,
        num_runs: int = 3
    ) -> Dict[str, Any]:
        """
        Run comparative benchmark between VectorBT and loop implementations.

        Args:
            vectorbt_fn: Function that runs VectorBT backtest
            loop_fn: Function that runs loop-based backtest
            data: OHLCV data
            signals: Trading signals
            num_runs: Number of runs to average

        Returns:
            Dict with comparison results
        """
        logger.info(f"Running performance comparison ({num_runs} runs each)")

        vbt_metrics = []
        loop_metrics = []

        # Run multiple iterations for statistical validity
        for i in range(num_runs):
            logger.info(f"Run {i+1}/{num_runs}...")

            # VectorBT
            vbt_perf = self.measure_backtest_performance(
                vectorbt_fn, data, signals, 'vectorbt'
            )
            vbt_metrics.append(vbt_perf)

            # Loop-based
            loop_perf = self.measure_backtest_performance(
                loop_fn, data, signals, 'loop'
            )
            loop_metrics.append(loop_perf)

        # Calculate averages
        avg_vbt_time = np.mean([m.execution_time_seconds for m in vbt_metrics])
        avg_loop_time = np.mean([m.execution_time_seconds for m in loop_metrics])

        speedup = avg_loop_time / avg_vbt_time if avg_vbt_time > 0 else 0

        return {
            'vectorbt': {
                'avg_time': avg_vbt_time,
                'avg_memory': np.mean([m.memory_mb for m in vbt_metrics]),
                'avg_throughput': np.mean([m.bars_per_second for m in vbt_metrics]),
                'runs': vbt_metrics
            },
            'loop': {
                'avg_time': avg_loop_time,
                'avg_memory': np.mean([m.memory_mb for m in loop_metrics]),
                'avg_throughput': np.mean([m.bars_per_second for m in loop_metrics]),
                'runs': loop_metrics
            },
            'speedup': speedup,
            'total_bars': len(data),
            'total_trades': loop_metrics[0].total_trades if loop_metrics else 0
        }

    def print_comparison(self, results: Dict[str, Any]):
        """Print formatted comparison results."""
        print("\n" + "="*70)
        print("VECTORBT vs LOOP-BASED PERFORMANCE COMPARISON")
        print("="*70)
        print(f"\nDataset size: {results['total_bars']:,} bars")
        print(f"Total trades: {results['total_trades']}")
        print("\nVectorBT Engine:")
        print(f"  Avg execution time: {results['vectorbt']['avg_time']:.3f}s")
        print(f"  Avg memory usage: {results['vectorbt']['avg_memory']:.1f}MB")
        print(f"  Throughput: {results['vectorbt']['avg_throughput']:,.0f} bars/sec")

        print("\nLoop-Based Engine:")
        print(f"  Avg execution time: {results['loop']['avg_time']:.3f}s")
        print(f"  Avg memory usage: {results['loop']['avg_memory']:.1f}MB")
        print(f"  Throughput: {results['loop']['avg_throughput']:,.0f} bars/sec")

        print(f"\nSPEEDUP: {results['speedup']:.1f}x faster with VectorBT")
        print("="*70 + "\n")


class OptimizationAnalyzer:
    """
    Analyze and provide recommendations for optimization performance.

    Tracks trial execution times, identifies bottlenecks, and suggests improvements.
    """

    def __init__(self):
        """Initialize optimization analyzer."""
        self.trial_times: List[float] = []
        self.trial_metrics: List[Dict[str, Any]] = []

    def record_trial(self, execution_time: float, metrics: Dict[str, Any]):
        """
        Record a single trial's performance.

        Args:
            execution_time: Trial execution time in seconds
            metrics: Backtest metrics for this trial
        """
        self.trial_times.append(execution_time)
        self.trial_metrics.append(metrics)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get optimization statistics.

        Returns:
            Dict with trial performance statistics
        """
        if not self.trial_times:
            return {}

        return {
            'total_trials': len(self.trial_times),
            'total_time': sum(self.trial_times),
            'avg_trial_time': np.mean(self.trial_times),
            'min_trial_time': np.min(self.trial_times),
            'max_trial_time': np.max(self.trial_times),
            'std_trial_time': np.std(self.trial_times),
            'trials_per_hour': 3600 / np.mean(self.trial_times) if self.trial_times else 0,
            'avg_trades_per_trial': np.mean([m.get('total_trades', 0) for m in self.trial_metrics])
        }

    def get_recommendations(self, data_size: int) -> List[str]:
        """
        Get performance optimization recommendations.

        Args:
            data_size: Number of data points being processed

        Returns:
            List of recommendations
        """
        recommendations = []
        stats = self.get_statistics()

        if not stats:
            return ["No trial data available for analysis"]

        avg_time = stats['avg_trial_time']

        # Recommendation logic
        if avg_time > 5.0:
            recommendations.append(
                "⚠️  Average trial time > 5s. Consider:\n"
                "   - Using smaller data subsets for initial optimization\n"
                "   - Reducing number of walk-forward splits\n"
                "   - Enabling trial pruning"
            )

        if data_size > 100000 and avg_time > 1.0:
            recommendations.append(
                "💡 Large dataset detected. Consider:\n"
                "   - Resampling to higher timeframes for initial optimization\n"
                "   - Using indicator caching (already implemented)\n"
                "   - Parallel optimization with more workers"
            )

        if stats['trials_per_hour'] < 100:
            recommendations.append(
                f"📊 Current throughput: {stats['trials_per_hour']:.0f} trials/hour\n"
                "   Consider increasing parallelization or using faster hardware"
            )

        if not recommendations:
            recommendations.append(
                f"✅ Performance is good! ({stats['trials_per_hour']:.0f} trials/hour)"
            )

        return recommendations

    def print_analysis(self, data_size: int):
        """Print formatted analysis and recommendations."""
        stats = self.get_statistics()

        print("\n" + "="*70)
        print("OPTIMIZATION PERFORMANCE ANALYSIS")
        print("="*70)

        if stats:
            print(f"\nTrial Statistics:")
            print(f"  Total trials: {stats['total_trials']}")
            print(f"  Total time: {stats['total_time']:.1f}s")
            print(f"  Avg trial time: {stats['avg_trial_time']:.3f}s ± {stats['std_trial_time']:.3f}s")
            print(f"  Min/Max: {stats['min_trial_time']:.3f}s / {stats['max_trial_time']:.3f}s")
            print(f"  Throughput: {stats['trials_per_hour']:.0f} trials/hour")
            print(f"  Avg trades/trial: {stats['avg_trades_per_trial']:.1f}")

            print("\nRecommendations:")
            for rec in self.get_recommendations(data_size):
                print(f"  {rec}")

        print("="*70 + "\n")

    def clear(self):
        """Clear all recorded trials."""
        self.trial_times.clear()
        self.trial_metrics.clear()
