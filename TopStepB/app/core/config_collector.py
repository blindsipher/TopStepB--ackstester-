"""
Configuration Collection
========================

Handles all user input collection for pipeline configuration.
Clean separation between CLI and interactive modes.
"""

import argparse
import sys
import os
from typing import Optional, List

from .state import PipelineState


def collect_cli_config() -> Optional[PipelineState]:
    """
    Collect configuration from command line arguments
    
    Returns:
        PipelineState if all required args provided, None otherwise
    """
    parser = argparse.ArgumentParser(description='Trading Strategy Pipeline')
    
    # Required arguments
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--symbol', required=True, help='Trading symbol (ES, NQ, etc.)')
    parser.add_argument('--timeframe', required=True, help='Timeframe (5m, 1h, etc.)')
    parser.add_argument('--account-type', required=True, help='Account type (topstep_50k, etc.)')
    parser.add_argument('--slippage', type=float, required=True, help='Slippage in ticks')
    parser.add_argument('--commission', type=float, required=True, help='Commission per trade')
    parser.add_argument('--contracts-per-trade', type=int, required=True, help='Number of contracts to trade per signal')
    parser.add_argument('--split-type', required=True, choices=['chronological', 'walk_forward'], help='Split method')
    parser.add_argument('--split-ratios', default='0.6,0.2,0.2', help='Train,validation,test ratios (sum=1.0, e.g., 0.6,0.2,0.2)')
    parser.add_argument('--gap-days', type=int, default=1, help='Gap days between splits to prevent leakage (default: 1)')
    
    # Optional arguments
    parser.add_argument('--data-file', help='Path to data file (optional)')
    parser.add_argument('--synthetic-bars', type=int, default=5000, help='Number of synthetic bars to generate (default: 5000)')
    
    # Optimization arguments
    parser.add_argument('--optimization-enabled', action='store_true', default=True, help='Enable parameter optimization (default: True)')
    parser.add_argument('--no-optimization', action='store_true', help='Disable parameter optimization')
    parser.add_argument('--max-trials', type=int, default=100, help='Maximum optimization trials (default: 100)')
    # Get default for help text
    default_workers = _get_default_workers()
    parser.add_argument('--max-workers', type=int, default=default_workers, help=f'Maximum parallel workers (default: {default_workers})')
    parser.add_argument('--memory-per-worker-mb', type=int, default=1500, help='Memory limit per worker in MB (default: 1500)')
    parser.add_argument('--timeout-per-trial', type=int, default=60, help='Maximum seconds per trial (default: 60)')
    parser.add_argument('--results-top-n', type=int, default=10, help='Number of top results to return (default: 10)')
    parser.add_argument(
        '--optuna-preset',
        choices=['aggressive', 'balanced', 'conservative'],
        default='aggressive',
        help='Optuna optimization preset: aggressive (fast, 30-50%% fewer trials), balanced (moderate), conservative (slow, thorough) - default: aggressive'
    )
    parser.add_argument(
        '--validation-tests',
        default='in_sample,out_of_sample,in_sample_permutation,out_of_sample_permutation',
        help='Comma-separated list of validation tests to run or "all"'
    )

    # Regime detection arguments
    parser.add_argument(
        '--use-regime-filter',
        action='store_true',
        help='Enable regime-based data filtering before optimization'
    )
    parser.add_argument(
        '--regime-types',
        default='trending',
        help='Comma-separated regime types to include: trending, mean_reverting, choppy (default: trending)'
    )
    parser.add_argument(
        '--regime-lookback',
        type=int,
        default=100,
        help='Lookback period for regime detection in bars (default: 100)'
    )
    parser.add_argument(
        '--min-regime-bars',
        type=int,
        default=200,
        help='Minimum bars required in selected regimes (default: 200)'
    )

    # Parse arguments
    try:
        args = parser.parse_args()
        
        
        # Handle optimization enabled/disabled logic
        optimization_enabled = args.optimization_enabled and not args.no_optimization
        
        # Validate max_workers
        validated_workers = _validate_workers(args.max_workers)
        
        # Normalize account type format: convert hyphens to underscores
        # CLI accepts both "topstep-50k" and "topstep_50k" but system expects "topstep_50k"
        normalized_account_type = args.account_type.replace('-', '_')
        
        # Normalize split type format: convert hyphens to underscores  
        # CLI accepts both "walk-forward" and "walk_forward" but system expects "walk_forward"
        normalized_split_type = args.split_type.replace('-', '_')
        
        # Parse split ratios
        try:
            ratios = tuple(float(x.strip()) for x in args.split_ratios.split(',') if x.strip())
            if len(ratios) != 3 or not (0.999 <= sum(ratios) <= 1.001):
                raise ValueError
        except Exception:
            print("Invalid --split-ratios; expected three comma-separated floats summing to 1.0 (e.g., 0.6,0.2,0.2)")
            return None
        
        validation_tests = [
            t.strip() for t in args.validation_tests.split(',') if t.strip()
        ]

        # Parse regime types
        regime_types = [
            r.strip() for r in args.regime_types.split(',') if r.strip()
        ] if args.use_regime_filter else []

        return PipelineState(
            strategy_name=args.strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
            account_type=normalized_account_type,
            slippage_ticks=args.slippage,
            commission_per_trade=args.commission,
            contracts_per_trade=args.contracts_per_trade,
            split_type=normalized_split_type,
            split_ratios=ratios,
            gap_days=int(args.gap_days),
            data_file_path=args.data_file,
            synthetic_bars=args.synthetic_bars,
            optimization_enabled=optimization_enabled,
            max_trials=args.max_trials,
            max_workers=validated_workers,
            memory_per_worker_mb=args.memory_per_worker_mb,
            timeout_per_trial=args.timeout_per_trial,
            results_top_n=args.results_top_n,
            optuna_preset=args.optuna_preset,
            validation_tests=validation_tests,
            use_regime_filter=args.use_regime_filter,
            regime_types=regime_types,
            regime_lookback=args.regime_lookback,
            min_regime_bars=args.min_regime_bars
        )
        
    except SystemExit:
        # argparse calls sys.exit on --help or invalid args
        return None


def collect_interactive_config(data_file_override: Optional[str] = None) -> PipelineState:
    """
    Collect configuration through interactive prompts.

    Args:
        data_file_override: Optional path to a data file supplied via CLI.
                            When provided, file selection prompts are skipped.

    Returns:
        PipelineState with user-provided configuration
    """
    print("\nInteractive Pipeline Configuration")
    print("=" * 40)
    
    # Strategy selection using discovery
    print("\n1. Strategy Selection:")
    strategy_name = _select_strategy_interactive()
    
    # Market configuration using existing config module
    print("\n2. Market Configuration:")
    symbol = _select_symbol_interactive()
    timeframe = _select_timeframe_interactive()
    account_type = _select_account_type_interactive()
    
    # Execution parameters
    print("\n3. Execution Parameters:")
    slippage_input = input("Enter slippage in ticks (default: 0.5): ").strip()
    slippage_ticks = float(slippage_input) if slippage_input else 0.5
    
    commission_input = input("Enter commission per trade (default: 2.50): ").strip()
    commission_per_trade = float(commission_input) if commission_input else 2.50
    
    contracts_input = input("Enter number of contracts per trade (default: 1): ").strip()
    contracts_per_trade = int(contracts_input) if contracts_input else 1
    
    # Data file (optional)
    print("\n4. Data Configuration:")
    data_file_path = data_file_override
    synthetic_bars = 5000

    if data_file_path:
        print(f"Using data file provided via CLI: {data_file_path}")
    else:
        use_file = input("Use data file? (y/N): ").strip().lower()
        if use_file in ['y', 'yes']:
            # Try to use tkinter file dialog
            try:
                import tkinter as tk
                from tkinter import filedialog
                print("Opening file dialog...")
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)  # Bring to front on Windows
                data_file_path = filedialog.askopenfilename(
                    title="Select Data File",
                    filetypes=[
                        ("Trading Data", ("*.csv", "*.parquet", "*.CSV", "*.PARQUET")),
                        ("CSV files", ("*.csv", "*.CSV")),
                        ("Parquet files", ("*.parquet", "*.PARQUET")),
                        ("All files", "*.*")
                    ]
                )
                root.destroy()
                if not data_file_path:
                    print("No file selected, will use synthetic data")
                else:
                    print(f"Selected file: {data_file_path}")
            except (ImportError, Exception) as e:
                print(f"File dialog failed ({e}), enter file path manually:")
                data_file_path = input("Enter data file path (or press Enter for synthetic): ").strip()
                if not data_file_path:
                    data_file_path = None

    # Ask for synthetic data amount if not using file
    if not data_file_path:
        bars_input = input("Enter number of synthetic bars to generate (default: 5000): ").strip()
        synthetic_bars = int(bars_input) if bars_input else 5000
    
    # Split configuration
    print("\n5. Data Split Configuration:")
    print("Split types: (1) chronological, (2) walk_forward")
    split_choice = input("Select split type (1 or 2): ").strip()
    split_type = "chronological" if split_choice == "1" else "walk_forward"
    ratios_input = input("Enter split ratios train,validation,test (default: 0.6,0.2,0.2): ").strip()
    if ratios_input:
        try:
            split_ratios = tuple(float(x.strip()) for x in ratios_input.split(',') if x.strip())
            if len(split_ratios) != 3 or not (0.999 <= sum(split_ratios) <= 1.001):
                raise ValueError
        except Exception:
            print("Invalid ratios; using default 0.6,0.2,0.2")
            split_ratios = (0.6, 0.2, 0.2)
    else:
        split_ratios = (0.6, 0.2, 0.2)
    gap_days_input = input("Gap days between splits (default: 1): ").strip()
    gap_days = int(gap_days_input) if gap_days_input else 1
    
    # Optimization configuration
    print("\n6. Optimization Configuration:")
    opt_enabled = input("Enable parameter optimization? (Y/n): ").strip().lower()
    optimization_enabled = opt_enabled not in ['n', 'no']
    
    max_trials = 100
    # Use existing optimization resource management instead of utils resource_manager
    import os
    max_workers = min(4, os.cpu_count() or 1)  # Conservative default that works with existing optimization
    memory_per_worker_mb = 1500  # Default memory per worker
    timeout_per_trial = 60
    results_top_n = 10
    if optimization_enabled:
        trials_input = input("Maximum optimization trials (default: 100): ").strip()
        max_trials = int(trials_input) if trials_input else 100
        
        cpu_count = os.cpu_count() or 1
        default_workers = _get_default_workers()
        workers_input = input(f"Maximum parallel workers (default: {default_workers}, system CPU cores: {cpu_count}): ").strip()
        raw_workers = int(workers_input) if workers_input else default_workers
        max_workers = _validate_workers(raw_workers)
        
        memory_input = input("Memory per worker in MB (default: 400): ").strip()
        memory_per_worker_mb = int(memory_input) if memory_input else 400
        
        timeout_input = input("Maximum seconds per trial (default: 60): ").strip()
        timeout_per_trial = int(timeout_input) if timeout_input else 60
        
        results_input = input("Number of top results to return (default: 10): ").strip()
        results_top_n = int(results_input) if results_input else 10
    
    
    # Validation configuration
    print("\n7. Validation Configuration:")
    tests_default = "in_sample,out_of_sample,in_sample_permutation,out_of_sample_permutation"
    tests_input = input(f"Validation tests (comma-separated or 'all') [default: {tests_default}]: ").strip()
    validation_tests = [t.strip() for t in (tests_input or tests_default).split(',') if t.strip()]

    # Regime detection configuration
    print("\n8. Regime Detection (Optional):")
    use_regime = input("Enable regime-based data filtering? (y/N): ").strip().lower()
    use_regime_filter = use_regime in ['y', 'yes']

    regime_types = []
    regime_lookback = 100
    min_regime_bars = 200

    if use_regime_filter:
        regime_input = input("Regime types to include (comma-separated: trending, mean_reverting, choppy) [default: trending]: ").strip()
        regime_types = [r.strip() for r in (regime_input or 'trending').split(',') if r.strip()]

        lookback_input = input("Regime lookback period in bars [default: 100]: ").strip()
        regime_lookback = int(lookback_input) if lookback_input else 100

        min_bars_input = input("Minimum bars required in selected regimes [default: 200]: ").strip()
        min_regime_bars = int(min_bars_input) if min_bars_input else 200

    return PipelineState(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        account_type=account_type,
        slippage_ticks=slippage_ticks,
        commission_per_trade=commission_per_trade,
        contracts_per_trade=contracts_per_trade,
        split_type=split_type,
        split_ratios=split_ratios,
        gap_days=gap_days,
        data_file_path=data_file_path,
        synthetic_bars=synthetic_bars,
        optimization_enabled=optimization_enabled,
        max_trials=max_trials,
        max_workers=max_workers,
        memory_per_worker_mb=memory_per_worker_mb,
        timeout_per_trial=timeout_per_trial,
        results_top_n=results_top_n,
        validation_tests=validation_tests,
        use_regime_filter=use_regime_filter,
        regime_types=regime_types,
        regime_lookback=regime_lookback,
        min_regime_bars=min_regime_bars
    )


def _select_from_list_interactive(prompt: str, options: List[str]) -> str:
    """
    Generic helper to present numbered options and return selection
    
    Args:
        prompt: The prompt to show user
        options: List of options to choose from
        
    Returns:
        Selected option string
    """
    # Handle empty option lists gracefully
    if not options:
        print("No options available.")
        return input("Enter value manually: ").strip()

    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    
    while True:
        choice = input(f"\n{prompt} (1-{len(options)}): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                selected_option = options[choice_num - 1]
                print(f"Selected: {selected_option}")
                return selected_option
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


def _select_strategy_interactive() -> str:
    """
    Interactive strategy selection using discovery
    
    Returns:
        Selected strategy name
    """
    try:
        # Import here to avoid circular imports
        from strategies import discover_strategies
        
        available_strategies = discover_strategies()
        strategy_names = list(available_strategies.keys())
        
        print("Available strategies:")
        return _select_from_list_interactive("Select strategy", strategy_names)
                
    except Exception as e:
        print(f"Error discovering strategies: {e}")
        print("Falling back to manual entry...")
        return input("Enter strategy name manually: ").strip()


def _select_symbol_interactive() -> str:
    """
    Interactive symbol selection using config module
    
    Returns:
        Selected symbol
    """
    try:
        # Import here to avoid circular imports
        from config.system_config import TopStepMarkets
        
        markets = TopStepMarkets()
        all_markets = markets.get_all_markets()
        available_symbols = list(all_markets.keys())
        
        print("Available symbols:")
        return _select_from_list_interactive("Select symbol", available_symbols)
        
    except Exception as e:
        print(f"Error loading symbols: {e}")
        return input("Enter symbol manually (ES, NQ, etc.): ").strip().upper()


def _select_timeframe_interactive() -> str:
    """
    Interactive timeframe selection using config module
    
    Returns:
        Selected timeframe
    """
    try:
        # Import here to avoid circular imports
        from config.system_config import SupportedTimeframes
        
        available_timeframes = SupportedTimeframes.SUPPORTED
        
        print("Available timeframes:")
        return _select_from_list_interactive("Select timeframe", available_timeframes)
        
    except Exception as e:
        print(f"Error loading timeframes: {e}")
        return input("Enter timeframe manually (5m, 1h, etc.): ").strip()


def _select_account_type_interactive() -> str:
    """
    Interactive account type selection
    
    Returns:
        Selected account type
    """
    # For now, use the known account types - could be made dynamic later
    available_accounts = ["topstep_50k", "topstep_100k", "topstep_150k"]
    
    print("Available account types:")
    return _select_from_list_interactive("Select account type", available_accounts)


def _get_default_workers() -> int:
    """
    Get intelligent default for max_workers based on environment variables and system specs.
    
    Returns:
        Validated default worker count
    """
    # First check environment variable (same as optuna config)
    if 'OPTUNA_MAX_WORKERS' in os.environ:
        try:
            env_workers = int(os.environ['OPTUNA_MAX_WORKERS'])
            return _validate_workers(env_workers)
        except (ValueError, TypeError):
            pass  # Fall through to computed default
    
    # Use optimized default based on CPU count (3x bandwidth improvement)
    cpu_count = os.cpu_count() or 1
    # Optimized: use 75% of available cores, minimum 1, maximum CPU_COUNT (removed -1 limitation)
    default = max(1, min(cpu_count, int(cpu_count * 0.75)))
    return default if default > 0 else 2  # Final fallback


def _validate_workers(workers: int) -> int:
    """
    Validate and potentially adjust worker count to reasonable bounds.
    
    Args:
        workers: Requested worker count
        
    Returns:
        Validated worker count within reasonable bounds
        
    Raises:
        ValueError: If workers is invalid and cannot be corrected
    """
    if workers < 1:
        raise ValueError(f"Worker count must be positive, got {workers}")
    
    cpu_count = os.cpu_count() or 1
    
    # Warn about potentially problematic configurations
    if workers > cpu_count * 2:
        print(f"Warning: {workers} workers exceeds recommended maximum ({cpu_count * 2}) for this system")
        print(f"   Consider using {min(workers, cpu_count * 2)} workers for better performance")
    
    # Hard limit: don't allow more than CPU_COUNT-1 workers to prevent system lockup
    max_workers = max(1, cpu_count - 1)
    if workers > max_workers:
        print(f"Warning: Limiting workers from {workers} to {max_workers} (CPU_COUNT-1) for system stability")
        workers = max_workers
    
    return workers


def is_cli_mode() -> bool:
    """
    Check if running in CLI mode (has command line arguments)
    
    Returns:
        True if CLI arguments provided, False for interactive mode
    """
    return len(sys.argv) > 1
