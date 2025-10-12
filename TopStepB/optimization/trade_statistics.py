"""
Trade Statistics Module
Calculates individual trade statistics for backtesting optimization
"""
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def calculate_trade_statistics(
    trade_dollar_pnls: List[float],
    total_trades: int,
    data_length: int
) -> Dict[str, float]:
    """
    Calculate comprehensive individual trade statistics.

    Args:
        trade_dollar_pnls: List of individual trade P&L values in dollars
        total_trades: Total number of completed trades
        data_length: Number of bars in the backtest period

    Returns:
        Dictionary with all trade statistics
    """
    try:
        if not trade_dollar_pnls or total_trades == 0:
            return get_default_trade_statistics()

        # Calculate basic statistics
        winning_trades = [pnl for pnl in trade_dollar_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_dollar_pnls if pnl < 0]

        stats = {}

        # Average win/loss
        stats['avg_win'] = float(np.mean(winning_trades)) if winning_trades else 0.0
        stats['avg_loss'] = float(abs(np.mean(losing_trades))) if losing_trades else 0.0

        # Best/worst trade
        stats['best_trade'] = float(max(trade_dollar_pnls)) if trade_dollar_pnls else 0.0
        stats['worst_trade'] = float(min(trade_dollar_pnls)) if trade_dollar_pnls else 0.0

        # Expectancy
        stats['expectancy'] = float(np.mean(trade_dollar_pnls)) if trade_dollar_pnls else 0.0

        # Trades per day (assuming 390 minutes per trading day for 5-min bars)
        trading_days = max(data_length / 78, 1)  # 78 5-min bars per day
        stats['trades_per_day'] = float(total_trades / trading_days)

        # Consecutive wins/losses
        stats['max_consecutive_wins'] = int(calculate_max_consecutive(trade_dollar_pnls, True))
        stats['max_consecutive_losses'] = int(calculate_max_consecutive(trade_dollar_pnls, False))

        return stats

    except Exception as e:
        logger.warning(f"Trade statistics calculation failed: {e}")
        return get_default_trade_statistics()


def calculate_max_consecutive(pnls: List[float], wins: bool) -> int:
    """
    Calculate maximum consecutive wins or losses.

    Args:
        pnls: List of trade P&L values
        wins: True for consecutive wins, False for consecutive losses

    Returns:
        Maximum consecutive count
    """
    if not pnls:
        return 0

    max_streak = 0
    current_streak = 0

    for pnl in pnls:
        if (wins and pnl > 0) or (not wins and pnl < 0):
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def get_default_trade_statistics() -> Dict[str, float]:
    """
    Return default values for trade statistics when no trades exist.

    Returns:
        Dictionary with zero values for all trade statistics
    """
    return {
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'best_trade': 0.0,
        'worst_trade': 0.0,
        'expectancy': 0.0,
        'trades_per_day': 0.0,
        'max_consecutive_wins': 0,
        'max_consecutive_losses': 0
    }


def aggregate_trade_statistics(split_results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate trade statistics across walk-forward splits.

    Args:
        split_results: List of result dictionaries from each split

    Returns:
        Aggregated trade statistics calculated from all individual trades
    """
    try:
        # Collect all individual trades from all splits
        all_trades = []
        total_trades = 0
        total_data_length = 0

        for result in split_results:
            if 'individual_trades' in result:
                individual = result['individual_trades']
                if isinstance(individual, (list, tuple)):
                    all_trades.extend(individual)

            total_trades += result.get('total_trades', 0)
            total_data_length += result.get('total_bars', 0)

        if not all_trades:
            return get_default_trade_statistics()

        # Calculate statistics from aggregated trades
        return calculate_trade_statistics(all_trades, total_trades, total_data_length)

    except Exception as e:
        logger.warning(f"Trade statistics aggregation failed: {e}")
        return get_default_trade_statistics()
