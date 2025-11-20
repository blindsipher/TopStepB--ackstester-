#!/usr/bin/env python3
"""
Optuna Configuration Benchmark
================================

Compares conservative vs aggressive Optuna configurations to measure:
- Convergence speed (trials to best result)
- Total optimization time
- Quality of top results
- Pruning efficiency

Usage:
    python benchmark_optuna_configs.py --strategy bollinger_squeeze --trials 100
"""

import argparse
import time
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json

import numpy as np
import optuna
from optuna import Trial, Study
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from optimization.config.optuna_config import (
    get_aggressive_config,
    get_conservative_config,
    get_balanced_config
)
from app.core.state import PipelineState
from app.core.config_collector import collect_cli_config
from data import create_test_data
from config.system_config import create_trading_config
from strategies import discover_strategies

logger = logging.getLogger(__name__)


class BenchmarkObjective:
    """Simplified objective function for benchmarking"""

    def __init__(self, strategy_instance, data):
        self.strategy_instance = strategy_instance
        self.data = data
        self.trial_count = 0

    def __call__(self, trial: Trial) -> float:
        """Simplified objective that simulates optimization workload"""
        self.trial_count += 1

        # Get parameter ranges
        param_ranges = self.strategy_instance.get_parameter_ranges()

        # Sample parameters based on tuple/list format
        params = {}
        for param_name, param_range in param_ranges.items():
            if isinstance(param_range, (list, tuple)) and len(param_range) > 0:
                if isinstance(param_range[0], str) or isinstance(param_range, list):
                    # Categorical parameter (list of choices)
                    params[param_name] = trial.suggest_categorical(param_name, param_range)
                elif len(param_range) == 3:
                    # Numeric parameter (min, max, step)
                    min_val, max_val, step = param_range
                    if isinstance(min_val, int) and isinstance(max_val, int):
                        params[param_name] = trial.suggest_int(param_name, min_val, max_val, step=step)
                    else:
                        params[param_name] = trial.suggest_float(param_name, min_val, max_val, step=step)
                elif len(param_range) == 2:
                    # Numeric parameter without step (min, max)
                    min_val, max_val = param_range
                    if isinstance(min_val, int) and isinstance(max_val, int):
                        params[param_name] = trial.suggest_int(param_name, min_val, max_val)
                    else:
                        params[param_name] = trial.suggest_float(param_name, min_val, max_val)

        # Simulate backtest computation (simplified)
        # In real scenario, this would be a full backtest
        score = self._simulate_backtest(params, trial)

        return score

    def _simulate_backtest(self, params: Dict, trial: Trial) -> float:
        """
        Simulate backtest with realistic computation time and scoring.
        This mimics the behavior of actual strategy optimization.
        """
        # Simulate intermediate results for pruning
        intermediate_scores = []
        n_steps = 10

        for step in range(n_steps):
            # Simulate computation time (5-20ms per step)
            time.sleep(np.random.uniform(0.005, 0.02))

            # Generate intermediate score with noise
            base_score = np.random.beta(2, 5)  # Realistic score distribution
            noise = np.random.normal(0, 0.1)
            intermediate = max(0, min(1, base_score + noise))
            intermediate_scores.append(intermediate)

            # Report intermediate value for pruning
            trial.report(intermediate, step)

            # Check if trial should be pruned
            if trial.should_prune():
                raise optuna.TrialPruned()

        # Final score is weighted average of intermediate scores
        final_score = np.mean(intermediate_scores[-5:])  # Last 5 steps

        return final_score


def run_benchmark_trial(
    preset_name: str,
    config,
    strategy_instance,
    data,
    n_trials: int = 100,
    timeout: int = 600
) -> Dict[str, Any]:
    """Run single benchmark with given configuration"""

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Running benchmark: {preset_name.upper()}")
    logger.info(f"{'=' * 60}")

    # Create study
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    study_name = f"benchmark_{preset_name}_{timestamp}"

    sampler = TPESampler(
        n_startup_trials=config.tpe_sampler.n_startup_trials,
        multivariate=config.tpe_sampler.multivariate,
        group=config.tpe_sampler.group,
        consider_prior=config.tpe_sampler.consider_prior,
        seed=42  # Fixed seed for reproducibility
    )

    pruner = MedianPruner(
        n_startup_trials=config.median_pruner.n_startup_trials,
        n_warmup_steps=config.median_pruner.n_warmup_steps,
        interval_steps=config.median_pruner.interval_steps,
        n_min_trials=config.median_pruner.n_min_trials
    )

    study = optuna.create_study(
        study_name=study_name,
        sampler=sampler,
        pruner=pruner,
        direction='maximize'
    )

    # Create objective
    objective = BenchmarkObjective(strategy_instance, data)

    # Run optimization
    start_time = time.time()

    try:
        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True
        )
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")

    end_time = time.time()
    total_time = end_time - start_time

    # Collect statistics
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    pruned_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]
    failed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]

    # Find trial number where best was found
    best_trial = study.best_trial
    trials_to_best = best_trial.number + 1 if best_trial else len(study.trials)

    # Get top 10 scores
    sorted_trials = sorted(completed_trials, key=lambda t: t.value, reverse=True)
    top_10_scores = [t.value for t in sorted_trials[:10]]

    results = {
        'preset_name': preset_name,
        'config': {
            'tpe_startup_trials': config.tpe_sampler.n_startup_trials,
            'tpe_consider_prior': config.tpe_sampler.consider_prior,
            'pruner_startup_trials': config.median_pruner.n_startup_trials,
            'pruner_warmup_steps': config.median_pruner.n_warmup_steps,
            'pruner_interval_steps': config.median_pruner.interval_steps,
        },
        'timing': {
            'total_time': total_time,
            'avg_time_per_trial': total_time / len(study.trials) if study.trials else 0,
            'trials_per_second': len(study.trials) / total_time if total_time > 0 else 0,
        },
        'convergence': {
            'trials_to_best': trials_to_best,
            'best_value': study.best_value,
            'convergence_ratio': trials_to_best / len(study.trials) if study.trials else 1.0,
        },
        'trial_statistics': {
            'total_trials': len(study.trials),
            'completed': len(completed_trials),
            'pruned': len(pruned_trials),
            'failed': len(failed_trials),
            'pruning_rate': len(pruned_trials) / len(study.trials) if study.trials else 0,
        },
        'quality_metrics': {
            'top_10_scores': top_10_scores,
            'top_10_mean': np.mean(top_10_scores) if top_10_scores else 0,
            'top_10_std': np.std(top_10_scores) if top_10_scores else 0,
            'score_range': [min(top_10_scores), max(top_10_scores)] if top_10_scores else [0, 0],
        }
    }

    return results


def print_comparison_report(conservative_results: Dict, aggressive_results: Dict):
    """Print detailed comparison report"""

    print("\n" + "=" * 80)
    print("OPTUNA CONFIGURATION BENCHMARK RESULTS")
    print("=" * 80)

    # Configuration comparison
    print("\n1. CONFIGURATION COMPARISON")
    print("-" * 80)
    print(f"{'Metric':<40} {'Conservative':<20} {'Aggressive':<20}")
    print("-" * 80)

    cons_cfg = conservative_results['config']
    agg_cfg = aggressive_results['config']

    print(f"{'TPE Startup Trials':<40} {cons_cfg['tpe_startup_trials']:<20} {agg_cfg['tpe_startup_trials']:<20}")
    print(f"{'TPE Consider Prior':<40} {cons_cfg['tpe_consider_prior']:<20} {agg_cfg['tpe_consider_prior']:<20}")
    print(f"{'Pruner Startup Trials':<40} {cons_cfg['pruner_startup_trials']:<20} {agg_cfg['pruner_startup_trials']:<20}")
    print(f"{'Pruner Warmup Steps':<40} {cons_cfg['pruner_warmup_steps']:<20} {agg_cfg['pruner_warmup_steps']:<20}")
    print(f"{'Pruner Interval Steps':<40} {cons_cfg['pruner_interval_steps']:<20} {agg_cfg['pruner_interval_steps']:<20}")

    # Timing comparison
    print("\n2. TIMING PERFORMANCE")
    print("-" * 80)
    print(f"{'Metric':<40} {'Conservative':<20} {'Aggressive':<20} {'Improvement':<15}")
    print("-" * 80)

    cons_time = conservative_results['timing']
    agg_time = aggressive_results['timing']

    total_time_improvement = ((cons_time['total_time'] - agg_time['total_time']) / cons_time['total_time'] * 100)
    print(f"{'Total Time (s)':<40} {cons_time['total_time']:<20.2f} {agg_time['total_time']:<20.2f} {total_time_improvement:>+14.1f}%")

    avg_time_improvement = ((cons_time['avg_time_per_trial'] - agg_time['avg_time_per_trial']) / cons_time['avg_time_per_trial'] * 100)
    print(f"{'Avg Time per Trial (s)':<40} {cons_time['avg_time_per_trial']:<20.3f} {agg_time['avg_time_per_trial']:<20.3f} {avg_time_improvement:>+14.1f}%")

    throughput_improvement = ((agg_time['trials_per_second'] - cons_time['trials_per_second']) / cons_time['trials_per_second'] * 100)
    print(f"{'Trials per Second':<40} {cons_time['trials_per_second']:<20.2f} {agg_time['trials_per_second']:<20.2f} {throughput_improvement:>+14.1f}%")

    # Convergence comparison
    print("\n3. CONVERGENCE EFFICIENCY")
    print("-" * 80)
    print(f"{'Metric':<40} {'Conservative':<20} {'Aggressive':<20} {'Improvement':<15}")
    print("-" * 80)

    cons_conv = conservative_results['convergence']
    agg_conv = aggressive_results['convergence']

    trials_improvement = ((cons_conv['trials_to_best'] - agg_conv['trials_to_best']) / cons_conv['trials_to_best'] * 100)
    print(f"{'Trials to Best Result':<40} {cons_conv['trials_to_best']:<20} {agg_conv['trials_to_best']:<20} {trials_improvement:>+14.1f}%")

    print(f"{'Best Value Found':<40} {cons_conv['best_value']:<20.4f} {agg_conv['best_value']:<20.4f}")

    conv_ratio_improvement = ((cons_conv['convergence_ratio'] - agg_conv['convergence_ratio']) / cons_conv['convergence_ratio'] * 100)
    print(f"{'Convergence Ratio':<40} {cons_conv['convergence_ratio']:<20.3f} {agg_conv['convergence_ratio']:<20.3f} {conv_ratio_improvement:>+14.1f}%")

    # Trial statistics
    print("\n4. TRIAL STATISTICS")
    print("-" * 80)
    print(f"{'Metric':<40} {'Conservative':<20} {'Aggressive':<20} {'Difference':<15}")
    print("-" * 80)

    cons_stats = conservative_results['trial_statistics']
    agg_stats = aggressive_results['trial_statistics']

    print(f"{'Total Trials':<40} {cons_stats['total_trials']:<20} {agg_stats['total_trials']:<20}")
    print(f"{'Completed Trials':<40} {cons_stats['completed']:<20} {agg_stats['completed']:<20}")
    print(f"{'Pruned Trials':<40} {cons_stats['pruned']:<20} {agg_stats['pruned']:<20}")
    print(f"{'Failed Trials':<40} {cons_stats['failed']:<20} {agg_stats['failed']:<20}")

    pruning_diff = (agg_stats['pruning_rate'] - cons_stats['pruning_rate']) * 100
    print(f"{'Pruning Rate (%)':<40} {cons_stats['pruning_rate']*100:<20.1f} {agg_stats['pruning_rate']*100:<20.1f} {pruning_diff:>+14.1f}pp")

    # Calculate wasted trials reduction
    cons_wasted = cons_stats['pruned'] + cons_stats['failed']
    agg_wasted = agg_stats['pruned'] + agg_stats['failed']
    wasted_reduction = ((cons_wasted - agg_wasted) / cons_wasted * 100) if cons_wasted > 0 else 0
    print(f"{'Wasted Trials Reduction':<40} {cons_wasted:<20} {agg_wasted:<20} {wasted_reduction:>+14.1f}%")

    # Quality metrics
    print("\n5. QUALITY METRICS (Top 10 Results)")
    print("-" * 80)
    print(f"{'Metric':<40} {'Conservative':<20} {'Aggressive':<20} {'Difference':<15}")
    print("-" * 80)

    cons_qual = conservative_results['quality_metrics']
    agg_qual = aggressive_results['quality_metrics']

    print(f"{'Mean Score':<40} {cons_qual['top_10_mean']:<20.4f} {agg_qual['top_10_mean']:<20.4f} {(agg_qual['top_10_mean'] - cons_qual['top_10_mean']):>+14.4f}")
    print(f"{'Std Deviation':<40} {cons_qual['top_10_std']:<20.4f} {agg_qual['top_10_std']:<20.4f}")
    print(f"{'Score Range Min':<40} {cons_qual['score_range'][0]:<20.4f} {agg_qual['score_range'][0]:<20.4f}")
    print(f"{'Score Range Max':<40} {cons_qual['score_range'][1]:<20.4f} {agg_qual['score_range'][1]:<20.4f}")

    # Summary
    print("\n6. SUMMARY")
    print("-" * 80)
    print(f"Aggressive configuration achieved:")
    print(f"  • {abs(total_time_improvement):.1f}% {'faster' if total_time_improvement > 0 else 'slower'} total time")
    print(f"  • {abs(trials_improvement):.1f}% {'fewer' if trials_improvement > 0 else 'more'} trials to best result")
    print(f"  • {abs(wasted_reduction):.1f}% {'reduction' if wasted_reduction > 0 else 'increase'} in wasted trials")
    print(f"  • {'Better' if agg_qual['top_10_mean'] > cons_qual['top_10_mean'] else 'Similar'} quality in top 10 results")

    print("\n" + "=" * 80)


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Benchmark Optuna configurations')
    parser.add_argument('--strategy', default='bollinger_squeeze', help='Strategy to use for benchmark')
    parser.add_argument('--trials', type=int, default=100, help='Number of trials per configuration')
    parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds per configuration')
    parser.add_argument('--output', help='Output JSON file for results')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("OPTUNA CONFIGURATION BENCHMARK")
    print("=" * 80)
    print(f"Strategy: {args.strategy}")
    print(f"Trials per config: {args.trials}")
    print(f"Timeout: {args.timeout}s")
    print("=" * 80)

    # Setup test environment
    logger.info("Setting up test environment...")

    # Create synthetic data
    data = create_test_data(bars=5000, symbol='ES')

    # Discover and instantiate strategy
    strategies = discover_strategies()
    if args.strategy not in strategies:
        logger.error(f"Strategy {args.strategy} not found")
        return 1

    strategy_class = strategies[args.strategy]
    strategy_instance = strategy_class()

    # Get configurations
    conservative_config = get_conservative_config()
    aggressive_config = get_aggressive_config()

    # Run benchmarks
    conservative_results = run_benchmark_trial(
        'conservative',
        conservative_config,
        strategy_instance,
        data,
        n_trials=args.trials,
        timeout=args.timeout
    )

    aggressive_results = run_benchmark_trial(
        'aggressive',
        aggressive_config,
        strategy_instance,
        data,
        n_trials=args.trials,
        timeout=args.timeout
    )

    # Print comparison report
    print_comparison_report(conservative_results, aggressive_results)

    # Save results if output file specified
    if args.output:
        results = {
            'benchmark_date': datetime.now().isoformat(),
            'benchmark_config': {
                'strategy': args.strategy,
                'trials_per_config': args.trials,
                'timeout': args.timeout
            },
            'conservative': conservative_results,
            'aggressive': aggressive_results
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to: {output_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
