"""
Display Formatting Utilities
Format data for display in the UI
"""
from typing import Any, Union
from datetime import datetime, timedelta

class NumberFormatter:
    """Format numeric values for display"""

    @staticmethod
    def format_currency(value: float, decimals: int = 2) -> str:
        """Format value as currency"""
        return f"${value:,.{decimals}f}"

    @staticmethod
    def format_percentage(value: float, decimals: int = 2) -> str:
        """Format value as percentage"""
        return f"{value:.{decimals}f}%"

    @staticmethod
    def format_number(value: float, decimals: int = 2) -> str:
        """Format number with thousand separators"""
        return f"{value:,.{decimals}f}"

    @staticmethod
    def format_integer(value: int) -> str:
        """Format integer with thousand separators"""
        return f"{value:,}"

    @staticmethod
    def format_ratio(value: float, decimals: int = 2) -> str:
        """Format ratio (e.g., Sharpe, Sortino)"""
        return f"{value:.{decimals}f}"

class DateFormatter:
    """Format date and time values"""

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime object"""
        if isinstance(dt, str):
            return dt
        return dt.strftime(format_str)

    @staticmethod
    def format_date(dt: datetime, format_str: str = "%Y-%m-%d") -> str:
        """Format date only"""
        if isinstance(dt, str):
            return dt
        return dt.strftime(format_str)

    @staticmethod
    def format_time(dt: datetime, format_str: str = "%H:%M:%S") -> str:
        """Format time only"""
        if isinstance(dt, str):
            return dt
        return dt.strftime(format_str)

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    @staticmethod
    def format_timedelta(td: timedelta) -> str:
        """Format timedelta in human-readable format"""
        total_seconds = td.total_seconds()
        return DateFormatter.format_duration(total_seconds)

class MetricFormatter:
    """Format trading metrics"""

    @staticmethod
    def format_pnl(value: float) -> str:
        """Format P&L with color indication"""
        color = "green" if value >= 0 else "red"
        formatted = NumberFormatter.format_currency(value)
        return formatted

    @staticmethod
    def format_win_rate(value: float) -> str:
        """Format win rate as percentage"""
        return NumberFormatter.format_percentage(value * 100, 1)

    @staticmethod
    def format_profit_factor(value: float) -> str:
        """Format profit factor"""
        return NumberFormatter.format_ratio(value, 2)

    @staticmethod
    def format_sharpe_ratio(value: float) -> str:
        """Format Sharpe ratio"""
        return NumberFormatter.format_ratio(value, 2)

    @staticmethod
    def format_sortino_ratio(value: float) -> str:
        """Format Sortino ratio"""
        return NumberFormatter.format_ratio(value, 2)

    @staticmethod
    def format_max_drawdown(value: float, as_percentage: bool = True) -> str:
        """Format max drawdown"""
        if as_percentage:
            return NumberFormatter.format_percentage(value * 100, 2)
        else:
            return NumberFormatter.format_currency(value)

    @staticmethod
    def format_trade_count(value: int) -> str:
        """Format trade count"""
        return NumberFormatter.format_integer(value)

class StatusFormatter:
    """Format status indicators"""

    @staticmethod
    def format_optimization_status(status: str) -> tuple:
        """
        Format optimization status with color
        Returns: (formatted_text, color)
        """
        status_map = {
            'running': ('Running', 'blue'),
            'completed': ('Completed', 'green'),
            'failed': ('Failed', 'red'),
            'paused': ('Paused', 'orange'),
            'stopped': ('Stopped', 'gray')
        }
        return status_map.get(status.lower(), (status, 'gray'))

    @staticmethod
    def format_trial_status(status: str) -> tuple:
        """
        Format trial status with color
        Returns: (formatted_text, color)
        """
        status_map = {
            'complete': ('Complete', 'green'),
            'pruned': ('Pruned', 'orange'),
            'fail': ('Failed', 'red'),
            'running': ('Running', 'blue')
        }
        return status_map.get(status.lower(), (status, 'gray'))

class TableFormatter:
    """Format data for tables"""

    @staticmethod
    def format_trial_row(trial_data: dict) -> dict:
        """Format trial data for display in table"""
        return {
            'Trial': trial_data.get('number', 'N/A'),
            'Score': NumberFormatter.format_number(trial_data.get('value', 0), 4),
            'PnL': MetricFormatter.format_pnl(trial_data.get('pnl', 0)),
            'Win Rate': MetricFormatter.format_win_rate(trial_data.get('win_rate', 0)),
            'Profit Factor': MetricFormatter.format_profit_factor(trial_data.get('profit_factor', 0)),
            'Max DD': MetricFormatter.format_max_drawdown(trial_data.get('max_drawdown', 0)),
            'Trades': MetricFormatter.format_trade_count(trial_data.get('trade_count', 0)),
            'Duration': DateFormatter.format_duration(trial_data.get('duration', 0)),
            'Status': trial_data.get('state', 'unknown')
        }

class ProgressFormatter:
    """Format progress indicators"""

    @staticmethod
    def format_progress_bar(current: int, total: int) -> tuple:
        """
        Format progress bar data
        Returns: (progress_fraction, progress_text)
        """
        if total == 0:
            return (0.0, "0/0 (0%)")

        progress = current / total
        percentage = progress * 100

        return (progress, f"{current}/{total} ({percentage:.1f}%)")

    @staticmethod
    def format_eta(elapsed_seconds: float, current: int, total: int) -> str:
        """Calculate and format estimated time remaining"""
        if current == 0 or total == 0:
            return "N/A"

        avg_time_per_item = elapsed_seconds / current
        remaining_items = total - current
        eta_seconds = avg_time_per_item * remaining_items

        return DateFormatter.format_duration(eta_seconds)
