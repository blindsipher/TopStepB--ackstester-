"""
VectorBT-Based Validation & Reporting
======================================

Simplified validation using VectorBT's built-in capabilities.
Replaces complex external dependencies with clean, integrated approach.

Features:
- Comprehensive metrics using VectorBT.stats()
- Custom report generation
- Trade-by-trade analysis
- Export to multiple formats
- No external dependencies (quantstats, etc.)
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from utils.logger import get_logger

logger = get_logger("vectorbt_validator")


class VectorBTValidator:
    """
    Comprehensive validation and reporting using VectorBT's built-in tools.

    This replaces the need for quantstats and provides:
    - All standard metrics
    - Custom futures-specific metrics
    - Trade analysis
    - Report generation
    - Export capabilities
    """

    def __init__(self, portfolio: vbt.Portfolio, strategy_name: str = "Strategy"):
        """
        Initialize validator with a VectorBT portfolio.

        Args:
            portfolio: VectorBT Portfolio object
            strategy_name: Name for reports
        """
        self.portfolio = portfolio
        self.strategy_name = strategy_name

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics using VectorBT's built-in stats.

        Returns:
            Dict with all metrics
        """
        # Get VectorBT's built-in stats (50+ metrics)
        stats = self.portfolio.stats()

        # Convert to dictionary
        stats_dict = stats.to_dict() if hasattr(stats, 'to_dict') else dict(stats)

        # Add custom futures-specific metrics
        custom_metrics = self._calculate_futures_metrics()
        stats_dict.update(custom_metrics)

        return stats_dict

    def get_composite_score_metrics(self, initial_cash: float = 50000) -> Dict[str, Any]:
        """
        Get metrics formatted for scorers.py CompositeScore.calculate_composite_score().

        This method extracts VectorBT portfolio statistics and formats them
        in the exact structure expected by the existing composite scoring system,
        enabling seamless integration with zero code changes to scorers.py.

        Args:
            initial_cash: Initial account equity (for dollar P&L calculations)

        Returns:
            Dict with metrics in scorers.py format containing all 7 required metrics:
            - daily_pnl_series: List of daily P&L values
            - equity_curve: List of daily equity values
            - sortino_ratio: Sortino ratio
            - pnl: Dollar-based P&L
            - max_drawdown: Max drawdown percentage
            - profit_factor: Profit factor
            - win_rate: Win rate percentage
            - total_trades: Total number of trades
            - total_bars: Total number of bars
        """
        # Get VectorBT stats
        stats = self.portfolio.stats()

        # Get equity curve (portfolio value over time)
        equity_curve = self.portfolio.value()

        # Calculate daily P&L series
        # VectorBT returns are in decimal format (0.02 = 2%)
        try:
            # Get portfolio returns (bar-by-bar)
            returns = self.portfolio.returns()

            # Resample to daily if we have datetime index
            if hasattr(equity_curve.index, 'date'):
                daily_equity = equity_curve.resample('D').last()
                daily_pnl = daily_equity.diff().fillna(0)
                daily_pnl_series = daily_pnl.tolist()
            else:
                # Fallback: use equity curve changes
                daily_pnl = equity_curve.diff().fillna(0)
                daily_pnl_series = daily_pnl.tolist()

        except Exception as e:
            logger.warning(f"Could not calculate daily P&L series: {e}")
            # Fallback: use total returns divided by number of bars
            total_return_pct = stats.get('Total Return [%]', 0)
            total_pnl = (total_return_pct / 100) * initial_cash
            num_bars = len(equity_curve)
            avg_pnl_per_bar = total_pnl / max(1, num_bars)
            daily_pnl_series = [avg_pnl_per_bar] * num_bars if num_bars > 0 else [0.0]

        # Get dollar-based max drawdown
        try:
            max_drawdown_dollars = float(self.portfolio.drawdown().max())
        except Exception as e:
            logger.warning(f"Could not calculate dollar drawdown: {e}")
            # Fallback: use percentage drawdown applied to initial cash
            max_dd_pct = stats.get('Max Drawdown [%]', 0)
            max_drawdown_dollars = abs(max_dd_pct / 100 * initial_cash)

        # Extract and convert metrics
        return {
            # Required for prop firm viability scoring
            'daily_pnl_series': daily_pnl_series,
            'equity_curve': equity_curve.tolist(),

            # Direct metrics from VectorBT stats
            'sortino_ratio': float(stats.get('Sortino Ratio', 0)),
            'profit_factor': float(stats.get('Profit Factor', 0)),
            'win_rate': float(stats.get('Win Rate [%]', 0)),
            'total_trades': int(stats.get('Total Trades', 0)),

            # Dollar-based metrics (institutional fix for account-equity independence)
            'total_dollar_pnl': float(stats.get('Total Profit', 0)),
            'dollar_pnl_for_optimization': float(stats.get('Total Profit', 0)),
            'max_drawdown_dollars': max_drawdown_dollars,
            'max_drawdown': float(stats.get('Max Drawdown [%]', 0)),  # Also include percentage
            'max_drawdown_percentage': float(stats.get('Max Drawdown [%]', 0)),

            # Trade frequency calculation
            'total_bars': len(self.portfolio.close),

            # Additional useful metrics
            'pnl': float(stats.get('Total Profit', 0)),  # Alias for compatibility
            'final_equity': float(self.portfolio.final_value()),
            'sharpe_ratio': float(stats.get('Sharpe Ratio', 0)),
            'calmar_ratio': float(stats.get('Calmar Ratio', 0)),

            # Return percentage for reference
            'total_return_pct': float(stats.get('Total Return [%]', 0)),
        }

    def _calculate_futures_metrics(self) -> Dict[str, Any]:
        """
        Calculate futures-specific metrics not in VectorBT defaults.

        Returns:
            Dict with custom metrics
        """
        trades = self.portfolio.trades

        if trades.count() == 0:
            return {
                'avg_trade_duration_bars': 0,
                'avg_winning_trade': 0,
                'avg_losing_trade': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'consecutive_wins_max': 0,
                'consecutive_losses_max': 0,
            }

        # Get trade data
        trade_pnls = trades.pnl.values

        # Calculate custom metrics
        winning_trades = trade_pnls[trade_pnls > 0]
        losing_trades = trade_pnls[trade_pnls < 0]

        return {
            'avg_trade_duration_bars': float(trades.duration.mean()),
            'avg_winning_trade': float(winning_trades.mean()) if len(winning_trades) > 0 else 0,
            'avg_losing_trade': float(losing_trades.mean()) if len(losing_trades) > 0 else 0,
            'largest_win': float(trade_pnls.max()),
            'largest_loss': float(trade_pnls.min()),
            'consecutive_wins_max': self._max_consecutive(trade_pnls > 0),
            'consecutive_losses_max': self._max_consecutive(trade_pnls < 0),
        }

    def _max_consecutive(self, boolean_array: np.ndarray) -> int:
        """Calculate maximum consecutive True values."""
        if len(boolean_array) == 0:
            return 0

        max_count = 0
        current_count = 0

        for val in boolean_array:
            if val:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count

    def get_trade_analysis(self) -> pd.DataFrame:
        """
        Get detailed trade-by-trade analysis.

        Returns:
            DataFrame with trade details
        """
        trades = self.portfolio.trades

        if trades.count() == 0:
            return pd.DataFrame()

        # Get trade records
        trade_df = pd.DataFrame({
            'entry_idx': trades.entry_idx.values,
            'exit_idx': trades.exit_idx.values,
            'entry_price': trades.entry_price.values,
            'exit_price': trades.exit_price.values,
            'size': trades.size.values,
            'pnl': trades.pnl.values,
            'return_pct': trades.return_.values * 100,
            'duration': trades.duration.values,
            'direction': ['Long' if s > 0 else 'Short' for s in trades.size.values],
        })

        # Add cumulative P&L
        trade_df['cumulative_pnl'] = trade_df['pnl'].cumsum()

        return trade_df

    def generate_text_report(self) -> str:
        """
        Generate comprehensive text report.

        Returns:
            Formatted text report
        """
        stats = self.get_comprehensive_stats()

        report = []
        report.append("="*70)
        report.append(f"STRATEGY VALIDATION REPORT: {self.strategy_name}")
        report.append("="*70)

        # Summary metrics
        report.append("\nPERFORMANCE SUMMARY:")
        report.append("-"*70)
        report.append(f"Total Return: {stats.get('Total Return [%]', 0):.2f}%")
        report.append(f"Total P&L: ${stats.get('Total Profit', 0):,.2f}")
        report.append(f"Sharpe Ratio: {stats.get('Sharpe Ratio', 0):.2f}")
        report.append(f"Sortino Ratio: {stats.get('Sortino Ratio', 0):.2f}")
        report.append(f"Max Drawdown: {stats.get('Max Drawdown [%]', 0):.2f}%")

        # Trade statistics
        report.append("\nTRADE STATISTICS:")
        report.append("-"*70)
        report.append(f"Total Trades: {stats.get('Total Trades', 0)}")
        report.append(f"Win Rate: {stats.get('Win Rate [%]', 0):.2f}%")
        report.append(f"Profit Factor: {stats.get('Profit Factor', 0):.2f}")
        report.append(f"Avg Trade: ${stats.get('avg_trade_pnl', 0):,.2f}")
        report.append(f"Avg Winner: ${stats.get('avg_winning_trade', 0):,.2f}")
        report.append(f"Avg Loser: ${stats.get('avg_losing_trade', 0):,.2f}")
        report.append(f"Largest Win: ${stats.get('largest_win', 0):,.2f}")
        report.append(f"Largest Loss: ${stats.get('largest_loss', 0):,.2f}")

        # Risk metrics
        report.append("\nRISK METRICS:")
        report.append("-"*70)
        report.append(f"Max Consecutive Wins: {stats.get('consecutive_wins_max', 0)}")
        report.append(f"Max Consecutive Losses: {stats.get('consecutive_losses_max', 0)}")
        report.append(f"Avg Trade Duration: {stats.get('avg_trade_duration_bars', 0):.1f} bars")

        report.append("="*70)

        return "\n".join(report)

    def export_to_json(self, filepath: Path) -> None:
        """Export metrics to JSON."""
        stats = self.get_comprehensive_stats()

        # Convert to JSON-serializable format
        json_data = {}
        for key, value in stats.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                json_data[key] = value
            elif isinstance(value, pd.Series):
                json_data[key] = value.to_list()
            else:
                json_data[key] = str(value)

        with open(filepath, 'w') as f:
            json.dump(json_data, f, indent=2)

        logger.info(f"Metrics exported to {filepath}")

    def export_trades_to_csv(self, filepath: Path) -> None:
        """Export trade analysis to CSV."""
        trade_df = self.get_trade_analysis()

        if not trade_df.empty:
            trade_df.to_csv(filepath, index=False)
            logger.info(f"Trades exported to {filepath}")
        else:
            logger.warning("No trades to export")

    def print_report(self):
        """Print report to console."""
        print(self.generate_text_report())


class ValidationComparator:
    """
    Compare VectorBT results with original loop-based implementation.

    Used to validate that VectorBT produces equivalent results.
    """

    def __init__(self, tolerance: float = 0.01):
        """
        Initialize comparator.

        Args:
            tolerance: Acceptable difference (1% default)
        """
        self.tolerance = tolerance

    def compare_metrics(
        self,
        vbt_metrics: Dict[str, Any],
        original_metrics: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Compare VectorBT metrics against original implementation.

        Args:
            vbt_metrics: Metrics from VectorBT
            original_metrics: Metrics from loop-based implementation

        Returns:
            Dict of metric_name -> matches (bool)
        """
        comparison = {}

        # Key metrics to compare
        compare_keys = [
            'total_trades',
            'total_dollar_pnl',
            'win_rate',
            'sharpe_ratio',
            'profit_factor',
            'max_drawdown_dollars',
        ]

        for key in compare_keys:
            vbt_val = vbt_metrics.get(key, 0)
            orig_val = original_metrics.get(key, 0)

            if vbt_val == 0 and orig_val == 0:
                comparison[key] = True
            elif orig_val == 0:
                comparison[key] = vbt_val == 0
            else:
                diff_pct = abs((vbt_val - orig_val) / orig_val)
                comparison[key] = diff_pct <= self.tolerance

        return comparison

    def print_comparison(
        self,
        vbt_metrics: Dict[str, Any],
        original_metrics: Dict[str, Any]
    ):
        """Print detailed comparison report."""
        comparison = self.compare_metrics(vbt_metrics, original_metrics)

        print("="*70)
        print("VECTORBT vs ORIGINAL COMPARISON")
        print("="*70)

        for key, matches in comparison.items():
            vbt_val = vbt_metrics.get(key, 0)
            orig_val = original_metrics.get(key, 0)
            status = "✓" if matches else "✗"

            print(f"{status} {key}:")
            print(f"    VectorBT: {vbt_val}")
            print(f"    Original: {orig_val}")
            if orig_val != 0:
                diff_pct = abs((vbt_val - orig_val) / orig_val) * 100
                print(f"    Difference: {diff_pct:.2f}%")

        print("="*70)

        all_match = all(comparison.values())
        if all_match:
            print("✓ ALL METRICS MATCH - VectorBT validated!")
        else:
            print("✗ Some metrics differ - review above")
        print("="*70)


def create_validation_report(
    portfolio: vbt.Portfolio,
    strategy_name: str,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Convenience function to create comprehensive validation report.

    Args:
        portfolio: VectorBT Portfolio object
        strategy_name: Strategy name
        output_dir: Optional directory for exports

    Returns:
        Dict with comprehensive stats
    """
    validator = VectorBTValidator(portfolio, strategy_name)

    # Get stats
    stats = validator.get_comprehensive_stats()

    # Print report
    validator.print_report()

    # Export if directory provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        validator.export_to_json(output_dir / f"{strategy_name}_metrics.json")
        validator.export_trades_to_csv(output_dir / f"{strategy_name}_trades.csv")

    return stats
