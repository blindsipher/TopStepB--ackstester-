"""
Out-of-Sample Testing Component
Run OOS backtests directly from the UI
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import sys
from typing import Dict, Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService
from src.ui.utils.formatters import format_currency, format_percentage, format_number


def render():
    """Render the OOS testing page"""
    st.header("Out-of-Sample Testing")

    st.markdown("""
    Test your optimized strategy parameters on fresh, unseen data to validate performance
    and prevent overfitting.
    """)

    db = DatabaseService()

    # Study selection
    st.markdown("---")
    st.subheader("Step 1: Select Study and Trial")

    studies = db.list_studies()
    if not studies:
        st.warning("No optimization studies found. Run an optimization first.")
        return

    study_names = [s['study_name'] for s in studies]
    selected_study = st.selectbox("Select Study", study_names, key="oos_study_select")

    if selected_study:
        # Get best trial
        best_trial = db.get_best_trial_with_metrics(selected_study)

        if not best_trial:
            st.warning("No completed trials found in this study.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Best Trial", f"#{best_trial['number']}")
        with col2:
            st.metric("Composite Score", f"{best_trial['value']:.4f}")
        with col3:
            metrics = best_trial.get('metrics', {})
            in_sample_pnl = metrics.get('total_dollar_pnl', metrics.get('total_pnl', 0))
            st.metric("In-Sample PnL", format_currency(in_sample_pnl))

        # Show parameters
        with st.expander("View Parameters", expanded=False):
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

        # OOS Configuration
        st.markdown("---")
        st.subheader("Step 2: Upload OOS Data and Configure")

        col1, col2 = st.columns(2)

        with col1:
            # File upload
            uploaded_file = st.file_uploader(
                "Upload OOS Data File",
                type=['csv', 'parquet'],
                help="Upload a CSV or Parquet file with OHLCV data for the OOS period"
            )

            if uploaded_file is not None:
                # Save uploaded file temporarily
                temp_path = Path("temp_oos_data") / uploaded_file.name
                temp_path.parent.mkdir(exist_ok=True)

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.success(f"✓ Uploaded: {uploaded_file.name}")

                # Try to load and show preview
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_preview = pd.read_csv(temp_path, nrows=5)
                    else:
                        df_preview = pd.read_parquet(temp_path)
                        df_preview = df_preview.head(5)

                    st.write("**Data Preview:**")
                    st.dataframe(df_preview)

                except Exception as e:
                    st.error(f"Error reading file: {e}")

        with col2:
            # OOS configuration
            strategy_name = selected_study.split('_')[0] if '_' in selected_study else 'bollinger_squeeze'
            symbol_from_study = selected_study.split('_')[1] if '_' in selected_study else 'ES'

            strategy = st.text_input("Strategy Name", value=strategy_name, disabled=True)
            symbol = st.selectbox("Symbol", ['ES', 'MES', 'NQ', 'MNQ', 'YM', 'MYM', 'RTY', 'M2K'],
                                 index=0 if symbol_from_study == 'ES' else 1 if symbol_from_study == 'MES' else 0)
            timeframe = st.selectbox("Timeframe", ['1m', '5m', '15m', '30m', '1h'], index=1)
            account_type = st.selectbox("Account Type", ['topstep_50k', 'topstep_100k', 'topstep_150k'])

        # Run OOS Backtest
        st.markdown("---")
        st.subheader("Step 3: Run OOS Backtest")

        if uploaded_file is None:
            st.info("👆 Upload OOS data file to continue")
        else:
            if st.button("▶ Run OOS Backtest", type="primary", use_container_width=True):
                run_oos_backtest(
                    db=db,
                    study_name=selected_study,
                    trial_number=best_trial['number'],
                    oos_data_path=temp_path,
                    strategy_name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    account_type=account_type,
                    in_sample_metrics=metrics
                )


def run_oos_backtest(
    db: DatabaseService,
    study_name: str,
    trial_number: int,
    oos_data_path: Path,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    account_type: str,
    in_sample_metrics: Dict[str, Any]
):
    """Run the OOS backtest and display results"""

    with st.spinner("Running OOS backtest... This may take a minute..."):
        try:
            from TopStepB.validation.oos_backtest import OOSBacktester

            # Get parameters
            params = db.get_trial_parameters(study_name, trial_number)

            # Create temporary parameters file
            params_data = {
                'study_name': study_name,
                'trial_number': trial_number,
                'parameters': params,
                'in_sample_metrics': in_sample_metrics
            }

            temp_params_path = Path("temp_oos_data") / "temp_params.json"
            with open(temp_params_path, 'w') as f:
                json.dump(params_data, f)

            # Run OOS backtest
            backtester = OOSBacktester()
            results = backtester.run_oos_backtest(
                parameters_file=str(temp_params_path),
                oos_data_file=str(oos_data_path),
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                account_type=account_type
            )

            if results:
                display_oos_results(results, in_sample_metrics)
            else:
                st.error("OOS backtest failed. Check logs for details.")

        except Exception as e:
            st.error(f"OOS backtest error: {e}")
            st.exception(e)


def display_oos_results(results: Dict[str, Any], in_sample_metrics: Dict[str, Any]):
    """Display OOS backtest results with visualizations"""

    st.markdown("---")
    st.header("📊 OOS Backtest Results")

    oos_metrics = results['oos_metrics']
    comparison = results['comparison']

    # Overview metrics
    st.subheader("Performance Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        is_pnl = comparison['total_dollar_pnl']['in_sample']
        oos_pnl = comparison['total_dollar_pnl']['oos']
        delta_pnl = oos_pnl - is_pnl
        st.metric("OOS Total PnL", format_currency(oos_pnl),
                 delta=format_currency(delta_pnl),
                 delta_color="normal")

    with col2:
        is_wr = comparison['win_rate']['in_sample']
        oos_wr = comparison['win_rate']['oos']
        delta_wr = oos_wr - is_wr
        st.metric("OOS Win Rate", format_percentage(oos_wr),
                 delta=f"{delta_wr:+.1f}%",
                 delta_color="normal")

    with col3:
        is_pf = comparison['profit_factor']['in_sample']
        oos_pf = comparison['profit_factor']['oos']
        delta_pf = oos_pf - is_pf
        st.metric("OOS Profit Factor", f"{oos_pf:.2f}",
                 delta=f"{delta_pf:+.2f}",
                 delta_color="normal")

    with col4:
        is_sr = comparison['sharpe_ratio']['in_sample']
        oos_sr = comparison['sharpe_ratio']['oos']
        delta_sr = oos_sr - is_sr
        st.metric("OOS Sharpe Ratio", f"{oos_sr:.2f}",
                 delta=f"{delta_sr:+.2f}",
                 delta_color="normal")

    # Detailed comparison table
    st.markdown("---")
    st.subheader("In-Sample vs OOS Comparison")

    comparison_data = []
    for metric, values in comparison.items():
        metric_name = metric.replace('_', ' ').title()
        comparison_data.append({
            'Metric': metric_name,
            'In-Sample': values['in_sample'],
            'OOS': values['oos'],
            'Change %': f"{values['change_pct']:+.1f}%"
        })

    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)

    # Performance interpretation
    st.markdown("---")
    st.subheader("Interpretation")

    pnl_change = comparison['total_dollar_pnl']['change_pct']
    wr_change = comparison['win_rate']['change_pct']
    pf_oos = comparison['profit_factor']['oos']

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Overall Assessment:**")

        if abs(pnl_change) <= 20 and abs(wr_change) <= 5 and pf_oos > 1.0:
            st.success("✅ **GOOD**: Strategy generalizes well to OOS data")
            st.write("• PnL degradation acceptable (< 20%)")
            st.write("• Win rate remains stable (< 5% change)")
            st.write("• Still profitable OOS")
        elif abs(pnl_change) <= 50 and pf_oos > 1.0:
            st.warning("⚠️ **ACCEPTABLE**: Some degradation but still viable")
            st.write("• Moderate performance decline")
            st.write("• Still profitable OOS")
            st.write("• Monitor closely in live trading")
        else:
            st.error("❌ **CONCERNING**: Significant degradation")
            st.write("• Large performance decline (> 50%)")
            st.write("• May indicate overfitting")
            st.write("• Review parameters or re-optimize")

    with col2:
        st.write("**Detailed Analysis:**")

        if pnl_change > -20:
            st.write("✓ PnL: Excellent retention")
        elif pnl_change > -50:
            st.write("⚠ PnL: Moderate degradation")
        else:
            st.write("✗ PnL: Significant decline")

        if abs(wr_change) < 5:
            st.write("✓ Win Rate: Very stable")
        elif abs(wr_change) < 10:
            st.write("⚠ Win Rate: Some variation")
        else:
            st.write("✗ Win Rate: Unstable")

        if pf_oos >= is_pf * 0.8:
            st.write("✓ Profit Factor: Good retention")
        elif pf_oos > 1.0:
            st.write("⚠ Profit Factor: Declined but profitable")
        else:
            st.write("✗ Profit Factor: Not profitable OOS")

    # Trade statistics comparison
    if 'avg_win' in oos_metrics and 'avg_win' in in_sample_metrics:
        st.markdown("---")
        st.subheader("Trade Statistics Comparison")

        trade_stats = ['avg_win', 'avg_loss', 'best_trade', 'worst_trade', 'expectancy']

        stats_data = []
        for stat in trade_stats:
            if stat in oos_metrics and stat in in_sample_metrics:
                is_val = in_sample_metrics[stat]
                oos_val = oos_metrics[stat]
                change = ((oos_val - is_val) / abs(is_val) * 100) if is_val != 0 else 0

                stats_data.append({
                    'Statistic': stat.replace('_', ' ').title(),
                    'In-Sample': format_currency(is_val) if 'trade' in stat or 'expectancy' in stat else f"${is_val:.2f}",
                    'OOS': format_currency(oos_val) if 'trade' in stat or 'expectancy' in stat else f"${oos_val:.2f}",
                    'Change %': f"{change:+.1f}%"
                })

        if stats_data:
            df_stats = pd.DataFrame(stats_data)
            st.dataframe(df_stats, use_container_width=True, hide_index=True)

    # OOS data info
    st.markdown("---")
    st.subheader("OOS Data Information")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("OOS Bars", format_number(results['oos_data_bars']))
    with col2:
        st.metric("OOS Trades", format_number(oos_metrics.get('total_trades', 0)))
    with col3:
        date_range = results['oos_date_range']
        st.write(f"**Date Range:**")
        st.write(date_range)

    # Save results button
    st.markdown("---")
    if st.button("💾 Save Results to JSON"):
        from TopStepB.validation.oos_backtest import OOSBacktester
        import pandas as pd

        backtester = OOSBacktester()
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"oos_results_{timestamp}.json"

        if backtester.save_oos_results(results, output_path):
            st.success(f"✓ Saved results to: {output_path}")
        else:
            st.error("Failed to save results")
