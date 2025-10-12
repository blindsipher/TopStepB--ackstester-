"""
TopStepB Backtester - Streamlit UI
Main Application Entry Point
"""
import streamlit as st
from streamlit_option_menu import option_menu
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.session_state import SessionState
from src.ui.components import configuration, data_loader, optimization_monitor, metrics_dashboard, results_dashboard, study_browser, oos_tester

# Page configuration
st.set_page_config(
    page_title="TopStepB Backtester",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""

    # Initialize session state
    SessionState.initialize()

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### TopStepB Backtester")
        st.markdown("---")

        selected = option_menu(
            menu_title=None,
            options=["Configuration", "Data Loader", "Run Optimization", "Monitor", "Metrics", "Results", "OOS Testing", "History"],
            icons=["gear", "file-earmark-bar-graph", "play-circle", "activity", "graph-up", "bar-chart", "clipboard-check", "clock-history"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "icon": {"color": "#1f77b4", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px"},
                "nav-link-selected": {"background-color": "#1f77b4"},
            }
        )

        st.markdown("---")

        # Show current optimization status if running
        if st.session_state.get('current_optimization'):
            st.info(f"Optimization Running: {st.session_state.current_optimization}")

        # PostgreSQL connection status
        try:
            from src.ui.services.database_service import DatabaseService
            db = DatabaseService()
            if db.test_connection():
                st.success("PostgreSQL Connected")
            else:
                st.warning("PostgreSQL Disconnected")
        except Exception as e:
            st.warning("PostgreSQL Not Available")

    # Main content area
    st.markdown('<h1 class="main-header">TopStepB Strategy Optimizer</h1>', unsafe_allow_html=True)

    # Route to appropriate page
    if selected == "Configuration":
        configuration.render()
    elif selected == "Data Loader":
        data_loader.render()
    elif selected == "Run Optimization":
        render_optimization_launcher()
    elif selected == "Monitor":
        optimization_monitor.render()
    elif selected == "Metrics":
        metrics_dashboard.render()
    elif selected == "Results":
        results_dashboard.render()
    elif selected == "OOS Testing":
        oos_tester.render()
    elif selected == "History":
        study_browser.render()

def render_optimization_launcher():
    """Render the optimization launch page"""
    st.header("Launch Optimization")

    # Check if configuration is complete
    if not st.session_state.get('configuration'):
        st.warning("Please complete the configuration first")
        if st.button("Go to Configuration"):
            st.rerun()
        return

    # Display current configuration summary
    st.subheader("Configuration Summary")
    config = st.session_state.configuration

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Strategy", config.get('strategy', 'N/A'))
        st.metric("Symbol", config.get('symbol', 'N/A'))
        st.metric("Timeframe", config.get('timeframe', 'N/A'))
    with col2:
        st.metric("Account Type", config.get('account_type', 'N/A'))
        st.metric("Slippage", f"{config.get('slippage', 0)} ticks")
        st.metric("Commission", f"${config.get('commission', 0)}")
    with col3:
        st.metric("Max Trials", config.get('max_trials', 100))
        st.metric("Workers", config.get('max_workers', 4))
        st.metric("Split Type", config.get('split_type', 'N/A'))

    st.markdown("---")

    # Data source display
    st.subheader("Data Source")
    data_file = st.session_state.get('data_file')
    synthetic_bars = st.session_state.get('synthetic_bars')

    if data_file:
        st.info(f"Data File: {data_file}")
    elif synthetic_bars:
        st.info(f"Synthetic Data: {synthetic_bars} bars")
    else:
        st.error("No data source selected! Please configure data in the Data Loader page.")
        return

    st.markdown("---")

    # Launch buttons
    st.subheader("Launch Controls")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if st.button("🚀 Launch Optimization", type="primary", use_container_width=True):
            launch_optimization()

    with col2:
        if st.button("✓ Validate Configuration", use_container_width=True):
            validate_configuration()

    with col3:
        if st.button("Clear", use_container_width=True):
            st.session_state.clear()
            st.success("Configuration cleared")
            st.rerun()

def launch_optimization():
    """Launch the optimization process"""
    try:
        from src.ui.services.pipeline_service import PipelineService

        pipeline = PipelineService()
        study_name = pipeline.start_optimization(st.session_state.configuration)

        st.session_state.current_optimization = study_name
        st.session_state.optimization_history = st.session_state.get('optimization_history', [])
        st.session_state.optimization_history.append(study_name)

        st.success(f"Optimization launched successfully! Study: {study_name}")
        st.info("Navigate to the 'Monitor' page to track progress")

    except Exception as e:
        st.error(f"Failed to launch optimization: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def validate_configuration():
    """Validate the current configuration"""
    from src.ui.utils.validators import ConfigurationValidator

    config = st.session_state.get('configuration', {})

    is_valid, errors = ConfigurationValidator.validate(config)

    if is_valid:
        st.success("Configuration is valid!")
    else:
        st.error("Configuration has errors:")
        for error in errors:
            st.markdown(f"- {error}")

if __name__ == "__main__":
    main()
