"""
Out-of-Sample (OOS) Backtest Runner
Runs backtests on new data using winning parameters from optimization
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import sys

# Add project root and TopStepB to path
project_root = Path(__file__).parent.parent.parent
topstepb_dir = project_root / "TopStepB"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(topstepb_dir))

from TopStepB.config.system_config import get_market_spec, configure_for_account
from TopStepB.data.data_loader import DataLoader
from TopStepB.optimization.objective import StatefulObjective

logger = logging.getLogger(__name__)


class OOSBacktester:
    """Run out-of-sample backtests with saved parameters"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def export_trial_parameters(
        self,
        study_name: str,
        trial_number: int,
        output_path: str,
        include_metrics: bool = True
    ) -> bool:
        """
        Export trial parameters to JSON file for OOS testing.

        Args:
            study_name: Name of the optimization study
            trial_number: Trial number to export
            output_path: Path to save JSON file
            include_metrics: Whether to include performance metrics

        Returns:
            True if successful, False otherwise
        """
        try:
            from src.ui.services.database_service import DatabaseService

            db = DatabaseService()

            # Get trial parameters
            params = db.get_trial_parameters(study_name, trial_number)
            if not params:
                self.logger.error(f"Trial {trial_number} not found in study {study_name}")
                return False

            # Build export data
            export_data = {
                'study_name': study_name,
                'trial_number': trial_number,
                'parameters': params,
                'export_timestamp': pd.Timestamp.now().isoformat()
            }

            # Optionally include metrics
            if include_metrics:
                metrics = db.get_trial_metrics(study_name, trial_number)
                export_data['in_sample_metrics'] = metrics

            # Save to JSON
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Exported parameters to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export parameters: {e}")
            return False

    def run_oos_backtest(
        self,
        parameters_file: str,
        oos_data_file: str,
        strategy_name: str,
        symbol: str = 'ES',
        timeframe: str = '5m',
        account_type: str = 'topstep_50k',
        slippage: float = 0.25,
        commission: float = 2.50
    ) -> Optional[Dict[str, Any]]:
        """
        Run out-of-sample backtest using saved parameters.

        Args:
            parameters_file: Path to JSON file with parameters
            oos_data_file: Path to OOS data file (CSV or Parquet)
            strategy_name: Name of strategy (e.g., 'bollinger_squeeze')
            symbol: Trading symbol
            timeframe: Data timeframe
            account_type: Account configuration
            slippage: Slippage in ticks
            commission: Commission per trade

        Returns:
            Dictionary with OOS backtest results
        """
        try:
            # Load saved parameters
            with open(parameters_file, 'r') as f:
                saved_data = json.load(f)

            params = saved_data['parameters']
            self.logger.info(f"Loaded parameters from trial {saved_data['trial_number']}")
            self.logger.info(f"In-sample study: {saved_data['study_name']}")

            # Load OOS data
            data_loader = DataLoader()
            data = data_loader.load_file(oos_data_file)

            if data is None or len(data) == 0:
                self.logger.error("Failed to load OOS data")
                return None

            self.logger.info(f"Loaded OOS data: {len(data)} bars from {data.index[0]} to {data.index[-1]}")

            # Get market and account config
            market_spec = get_market_spec(symbol)
            account_config = configure_for_account(account_type, verbose=False)

            # Create trading config
            from dataclasses import dataclass
            from decimal import Decimal

            @dataclass
            class TradingConfig:
                market_spec: Any
                account: Any
                slippage_ticks: Decimal
                commission_per_trade: Decimal
                contracts_per_trade: int = 1

            trading_config = TradingConfig(
                market_spec=market_spec,
                account=account_config,
                slippage_ticks=Decimal(str(slippage)),
                commission_per_trade=Decimal(str(commission)),
                contracts_per_trade=1
            )

            # Import and instantiate strategy
            strategy_module = __import__(
                f'TopStepB.strategies.{strategy_name}.strategy',
                fromlist=['']
            )

            # Find the strategy class dynamically
            # Convert strategy_name to class name (e.g., "bollinger_squeeze" -> "BollingerSqueezeStrategy")
            class_name_parts = [part.capitalize() for part in strategy_name.split('_')]
            expected_class_name = ''.join(class_name_parts) + 'Strategy'

            strategy_class = getattr(strategy_module, expected_class_name, None)

            if strategy_class is None:
                # Fallback: try to find any class ending with 'Strategy'
                for name in dir(strategy_module):
                    if name.endswith('Strategy') and not name.startswith('_'):
                        strategy_class = getattr(strategy_module, name)
                        break

            if strategy_class is None:
                raise ValueError(f"No strategy class found in {strategy_name}.strategy")

            # Convert parameters to correct types
            typed_params = {}
            for key, value in params.items():
                # Handle boolean parameters (0.0 or 1.0)
                if key.startswith('use_') or key.endswith('_filter'):
                    typed_params[key] = bool(int(value))
                elif key.endswith('_method'):
                    typed_params[key] = int(value)
                else:
                    typed_params[key] = float(value)

            self.logger.info(f"Running strategy with {len(typed_params)} parameters")

            # Instantiate strategy with parameters
            strategy = strategy_class(**typed_params)

            # Generate signals
            signals = strategy.generate_signals(data)

            # Import execution engine
            from execution.simple_executor import SimpleExecutor

            # Run backtest with execution engine
            executor = SimpleExecutor(trading_config)
            trades = executor.execute_backtest(data, signals)

            self.logger.info(f"Generated {len(trades)} trades")

            # Calculate metrics from trades
            from optimization.metrics import calculate_metrics_from_trades
            oos_metrics = calculate_metrics_from_trades(trades, data, trading_config)

            # Build result summary
            summary = {
                'oos_data_file': oos_data_file,
                'oos_data_bars': len(data),
                'oos_date_range': f"{data.index[0]} to {data.index[-1]}",
                'parameters_used': params,
                'in_sample_metrics': saved_data.get('in_sample_metrics', {}),
                'oos_metrics': oos_metrics,
                'comparison': self._compare_metrics(
                    saved_data.get('in_sample_metrics', {}),
                    oos_metrics
                )
            }

            return summary

        except Exception as e:
            self.logger.error(f"OOS backtest failed: {e}", exc_info=True)
            return None

    def _compare_metrics(
        self,
        in_sample: Dict[str, Any],
        oos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare in-sample and OOS metrics."""
        comparison = {}

        key_metrics = [
            'total_dollar_pnl', 'total_trades', 'win_rate',
            'profit_factor', 'sharpe_ratio', 'max_drawdown'
        ]

        for metric in key_metrics:
            is_value = in_sample.get(metric, 0)
            oos_value = oos.get(metric, 0)

            if is_value != 0:
                pct_change = ((oos_value - is_value) / abs(is_value)) * 100
            else:
                pct_change = 0

            comparison[metric] = {
                'in_sample': is_value,
                'oos': oos_value,
                'change_pct': pct_change
            }

        return comparison

    def save_oos_results(self, results: Dict[str, Any], output_path: str) -> bool:
        """Save OOS backtest results to JSON file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            self.logger.info(f"Saved OOS results to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save OOS results: {e}")
            return False


def main():
    """Command-line interface for OOS backtesting."""
    import argparse

    parser = argparse.ArgumentParser(description='Run out-of-sample backtest with saved parameters')
    parser.add_argument('--export', action='store_true', help='Export trial parameters')
    parser.add_argument('--study', type=str, help='Study name')
    parser.add_argument('--trial', type=int, help='Trial number')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--params', type=str, help='Parameters JSON file')
    parser.add_argument('--data', type=str, help='OOS data file')
    parser.add_argument('--strategy', type=str, default='bollinger_squeeze', help='Strategy name')
    parser.add_argument('--symbol', type=str, default='ES', help='Trading symbol')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    backtester = OOSBacktester()

    if args.export:
        # Export mode
        if not args.study or args.trial is None or not args.output:
            print("Error: --export requires --study, --trial, and --output")
            return

        success = backtester.export_trial_parameters(
            args.study,
            args.trial,
            args.output
        )

        if success:
            print(f"✓ Exported parameters to {args.output}")
        else:
            print("✗ Export failed")

    else:
        # Run OOS backtest
        if not args.params or not args.data:
            print("Error: OOS backtest requires --params and --data")
            return

        print(f"Running OOS backtest...")
        print(f"  Parameters: {args.params}")
        print(f"  OOS Data: {args.data}")
        print(f"  Strategy: {args.strategy}")
        print()

        results = backtester.run_oos_backtest(
            parameters_file=args.params,
            oos_data_file=args.data,
            strategy_name=args.strategy,
            symbol=args.symbol
        )

        if results:
            print("\n=== OOS BACKTEST RESULTS ===\n")
            print(f"OOS Data: {results['oos_data_bars']} bars")
            print(f"Date Range: {results['oos_date_range']}\n")

            print("Performance Comparison:")
            for metric, values in results['comparison'].items():
                print(f"  {metric}:")
                print(f"    In-Sample: {values['in_sample']}")
                print(f"    OOS: {values['oos']}")
                print(f"    Change: {values['change_pct']:+.1f}%")

            # Save results
            if args.output:
                backtester.save_oos_results(results, args.output)
                print(f"\n✓ Saved results to {args.output}")

        else:
            print("✗ OOS backtest failed")


if __name__ == '__main__':
    main()
