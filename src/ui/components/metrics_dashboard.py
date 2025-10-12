"""
Metrics Dashboard Component
Displays detailed performance metrics for optimization trials
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService
from src.ui.utils.formatters import format_currency, format_percentage, format_number, format_ratio

def render():
    """Render the metrics dashboard page"""
    st.header("Performance Metrics Dashboard")

    st.info("""
    **Note**: Detailed metrics are only available for trials run after this update.
    Existing trials only have the composite score.

    To see detailed metrics, run a new optimization and return to this page.
    """)

    # Initialize database service
    db = DatabaseService()

    # Study selection
    studies = db.list_studies(limit=100)
    if not studies:
        st.warning("No optimization studies found in database.")
        st.write("Run an optimization first to see results here.")
        return

    study_names = [s['study_name'] for s in studies]
    selected_study = st.selectbox(
        "Select Study",
        study_names,
        help="Choose an optimization study to view metrics"
    )

    if not selected_study:
        return

    st.markdown("---")

    # Get best trial with metrics
    best_trial = db.get_best_trial_with_metrics(selected_study)

    if not best_trial:
        st.warning("No completed trials found for this study.")
        return

    # Check if metrics exist
    metrics = best_trial.get('metrics', {})

    st.subheader(f"Best Trial #{best_trial['number']}")
    st.write(f"**Composite Score:** {best_trial['value']:.4f}")
    st.write(f"**Completed:** {best_trial['datetime_complete']}")

    if not metrics:
        st.warning("""
        **Detailed metrics not available for this trial.**

        This trial was run before the metrics update. To see detailed performance metrics:
        1. Go to "Run Optimization" page
        2. Run a new optimization (even just 10-20 trials)
        3. Return to this page to see:
           - Total P&L
           - Win Rate
           - Number of Trades
           - Max Drawdown
           - Sharpe/Sortino Ratios
           - Profit Factor
           - And much more!
        """)

        # Show parameters at least
        st.markdown("---")
        st.subheader("Best Trial Parameters")
        params = db.get_trial_parameters(selected_study, best_trial['number'])
        if params:
            col1, col2 = st.columns(2)
            items = list(params.items())
            mid = len(items) // 2

            with col1:
                for k, v in items[:mid]:
                    st.write(f"**{k}:** {v}")

            with col2:
                for k, v in items[mid:]:
                    st.write(f"**{k}:** {v}")
        return

    # Data Statistics (if available)
    st.markdown("---")
    st.subheader("Backtest Data Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        data_bars = metrics.get('total_bars', metrics.get('num_bars', 'N/A'))
        st.metric(
            "Bars Processed",
            format_number(data_bars) if data_bars != 'N/A' else 'N/A',
            help="Total number of price bars analyzed"
        )

    with col2:
        trading_days = metrics.get('trading_days', 'N/A')
        st.metric(
            "Trading Days",
            format_number(trading_days) if trading_days != 'N/A' else 'N/A',
            help="Number of trading days in the backtest"
        )

    with col3:
        date_start = metrics.get('date_start', 'N/A')
        st.metric(
            "Start Date",
            str(date_start)[:10] if date_start != 'N/A' else 'N/A',
            help="First date in backtest data"
        )

    with col4:
        date_end = metrics.get('date_end', 'N/A')
        st.metric(
            "End Date",
            str(date_end)[:10] if date_end != 'N/A' else 'N/A',
            help="Last date in backtest data"
        )

    # Display detailed metrics
    st.markdown("---")
    st.subheader("Key Performance Indicators")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_pnl = metrics.get('total_dollar_pnl', metrics.get('total_pnl', 0))
        st.metric(
            "Total P&L",
            format_currency(total_pnl),
            help="Total profit/loss in dollars"
        )

    with col2:
        num_trades = metrics.get('num_trades', 0)
        st.metric(
            "Number of Trades",
            format_number(num_trades),
            help="Total number of trades executed"
        )

    with col3:
        win_rate = metrics.get('win_rate', 0)
        st.metric(
            "Win Rate",
            format_percentage(win_rate),
            help="Percentage of winning trades"
        )

    with col4:
        profit_factor = metrics.get('profit_factor', 0)
        st.metric(
            "Profit Factor",
            format_ratio(profit_factor),
            help="Ratio of gross profit to gross loss"
        )

    # Risk Metrics
    st.markdown("---")
    st.subheader("Risk Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        max_dd = metrics.get('max_drawdown', 0)
        max_dd_dollars = metrics.get('max_drawdown_dollars', 0)
        st.metric(
            "Max Drawdown",
            format_percentage(max_dd),
            delta=format_currency(max_dd_dollars),
            delta_color="inverse",
            help="Maximum peak-to-trough decline"
        )

    with col2:
        sharpe = metrics.get('sharpe_ratio', 0)
        st.metric(
            "Sharpe Ratio",
            format_ratio(sharpe),
            help="Risk-adjusted return metric"
        )

    with col3:
        sortino = metrics.get('sortino_ratio', 0)
        st.metric(
            "Sortino Ratio",
            format_ratio(sortino),
            help="Downside risk-adjusted return"
        )

    with col4:
        calmar = metrics.get('calmar_ratio', 0)
        st.metric(
            "Calmar Ratio",
            format_ratio(calmar),
            help="Return over maximum drawdown"
        )

    # Trade Statistics
    st.markdown("---")
    st.subheader("Trade Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Averages:**")
        st.write(f"  Average Win: {format_currency(metrics.get('avg_win', 0))}")
        st.write(f"  Average Loss: {format_currency(metrics.get('avg_loss', 0))}")
        st.write(f"  Expectancy: {format_currency(metrics.get('expectancy', 0))}")
        st.write(f"  Trades Per Day: {metrics.get('trades_per_day', 0):.2f}")

    with col2:
        st.write("**Extremes:**")
        st.write(f"  Best Trade: {format_currency(metrics.get('best_trade', 0))}")
        st.write(f"  Worst Trade: {format_currency(metrics.get('worst_trade', 0))}")
        st.write(f"  Max Consecutive Wins: {format_number(metrics.get('max_consecutive_wins', 0))}")
        st.write(f"  Max Consecutive Losses: {format_number(metrics.get('max_consecutive_losses', 0))}")

    # Show parameters
    st.markdown("---")
    st.subheader("Winning Parameters")

    params = db.get_trial_parameters(selected_study, best_trial['number'])
    if params:
        col1, col2 = st.columns(2)
        items = list(params.items())
        mid = len(items) // 2

        with col1:
            for k, v in items[:mid]:
                st.write(f"**{k}:** {v}")

        with col2:
            for k, v in items[mid:]:
                st.write(f"**{k}:** {v}")
