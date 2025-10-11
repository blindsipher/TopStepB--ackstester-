"""
Configuration Component
User interface for setting up optimization parameters
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.session_state import SessionState
from src.ui.utils.validators import ConfigurationValidator

def render():
    """Render the configuration page"""
    st.header("Configuration")

    # Strategy discovery
    strategies = discover_strategies()

    # Create tabs for organization
    tab1, tab2, tab3, tab4 = st.tabs(["Strategy & Market", "Execution", "Optimization", "Validation"])

    with tab1:
        render_strategy_market_config(strategies)

    with tab2:
        render_execution_config()

    with tab3:
        render_optimization_config()

    with tab4:
        render_validation_config()

    # Configuration actions
    st.markdown("---")
    render_config_actions()

def discover_strategies():
    """Discover available strategies from the strategies directory"""
    try:
        strategies_dir = project_root / "TopStepB" / "strategies"
        if not strategies_dir.exists():
            return ["bollinger_squeeze"]  # Default fallback

        strategies = []
        for item in strategies_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                strategies.append(item.name)

        return sorted(strategies) if strategies else ["bollinger_squeeze"]
    except Exception:
        return ["bollinger_squeeze"]

def render_strategy_market_config(strategies):
    """Render strategy and market configuration section"""
    st.subheader("Strategy & Market Parameters")

    col1, col2 = st.columns(2)

    with col1:
        # Strategy selection
        current_strategy = st.session_state.get('configuration', {}).get('strategy', strategies[0])
        strategy = st.selectbox(
            "Strategy",
            options=strategies,
            index=strategies.index(current_strategy) if current_strategy in strategies else 0,
            help="Select the trading strategy to optimize"
        )
        SessionState.update_configuration('strategy', strategy)

        # Symbol
        symbols = ConfigurationValidator.VALID_SYMBOLS
        current_symbol = st.session_state.get('configuration', {}).get('symbol', 'ES')
        symbol = st.selectbox(
            "Symbol",
            options=symbols,
            index=symbols.index(current_symbol) if current_symbol in symbols else 0,
            help="Trading instrument symbol"
        )
        SessionState.update_configuration('symbol', symbol)

        # Timeframe
        timeframes = ConfigurationValidator.VALID_TIMEFRAMES
        current_timeframe = st.session_state.get('configuration', {}).get('timeframe', '5m')
        timeframe = st.selectbox(
            "Timeframe",
            options=timeframes,
            index=timeframes.index(current_timeframe) if current_timeframe in timeframes else 1,
            help="Bar size for backtesting"
        )
        SessionState.update_configuration('timeframe', timeframe)

    with col2:
        # Account type
        account_types = ConfigurationValidator.VALID_ACCOUNT_TYPES
        current_account = st.session_state.get('configuration', {}).get('account_type', 'topstep_50k')
        account_type = st.selectbox(
            "Account Type",
            options=account_types,
            index=account_types.index(current_account) if current_account in account_types else 0,
            help="TopStep account type and rules"
        )
        SessionState.update_configuration('account_type', account_type)

        # Split type
        split_types = ConfigurationValidator.VALID_SPLIT_TYPES
        current_split = st.session_state.get('configuration', {}).get('split_type', 'walk_forward')
        split_type = st.selectbox(
            "Data Split Type",
            options=split_types,
            index=split_types.index(current_split) if current_split in split_types else 0,
            help="How to split data for train/validate/test"
        )
        SessionState.update_configuration('split_type', split_type)

        # Split ratios
        current_ratios = st.session_state.get('configuration', {}).get('split_ratios', '0.6,0.2,0.2')
        split_ratios = st.text_input(
            "Split Ratios (train,validate,test)",
            value=current_ratios,
            help="Comma-separated ratios that sum to 1.0"
        )
        SessionState.update_configuration('split_ratios', split_ratios)

        # Gap days
        current_gap = st.session_state.get('configuration', {}).get('gap_days', 1)
        gap_days = st.number_input(
            "Gap Days",
            min_value=0,
            max_value=30,
            value=current_gap,
            help="Days between splits to prevent data leakage"
        )
        SessionState.update_configuration('gap_days', gap_days)

def render_execution_config():
    """Render execution configuration section"""
    st.subheader("Execution Parameters")

    col1, col2 = st.columns(2)

    with col1:
        # Slippage
        current_slippage = st.session_state.get('configuration', {}).get('slippage', 0.25)
        slippage = st.number_input(
            "Slippage (ticks)",
            min_value=0.0,
            max_value=10.0,
            value=current_slippage,
            step=0.25,
            help="Expected slippage per trade in ticks"
        )
        SessionState.update_configuration('slippage', slippage)

        # Commission
        current_commission = st.session_state.get('configuration', {}).get('commission', 2.50)
        commission = st.number_input(
            "Commission ($)",
            min_value=0.0,
            max_value=50.0,
            value=current_commission,
            step=0.50,
            help="Commission cost per trade"
        )
        SessionState.update_configuration('commission', commission)

    with col2:
        # Contracts per trade
        current_contracts = st.session_state.get('configuration', {}).get('contracts_per_trade', 1)
        contracts = st.number_input(
            "Contracts Per Trade",
            min_value=1,
            max_value=100,
            value=current_contracts,
            help="Position size in contracts"
        )
        SessionState.update_configuration('contracts_per_trade', contracts)

def render_optimization_config():
    """Render optimization configuration section"""
    st.subheader("Optimization Settings")

    col1, col2 = st.columns(2)

    with col1:
        # Max trials
        current_trials = st.session_state.get('configuration', {}).get('max_trials', 100)
        max_trials = st.number_input(
            "Maximum Trials",
            min_value=1,
            max_value=100000,
            value=current_trials,
            step=10,
            help="Maximum number of parameter combinations to test"
        )
        SessionState.update_configuration('max_trials', max_trials)

        # Max workers
        current_workers = st.session_state.get('configuration', {}).get('max_workers', 4)
        max_workers = st.number_input(
            "Maximum Workers",
            min_value=1,
            max_value=64,
            value=current_workers,
            help="Number of parallel optimization workers"
        )
        SessionState.update_configuration('max_workers', max_workers)

        # Results top N
        current_top_n = st.session_state.get('configuration', {}).get('results_top_n', 10)
        results_top_n = st.number_input(
            "Top Results to Return",
            min_value=1,
            max_value=500,
            value=current_top_n,
            help="Number of best parameter sets to save"
        )
        SessionState.update_configuration('results_top_n', results_top_n)

    with col2:
        # Memory per worker
        current_memory = st.session_state.get('configuration', {}).get('memory_per_worker_mb', 1500)
        memory_limit = st.number_input(
            "Memory Per Worker (MB)",
            min_value=512,
            max_value=8192,
            value=current_memory,
            step=256,
            help="Memory limit for each worker process"
        )
        SessionState.update_configuration('memory_per_worker_mb', memory_limit)

        # Timeout per trial
        current_timeout = st.session_state.get('configuration', {}).get('timeout_per_trial', 60)
        timeout = st.number_input(
            "Timeout Per Trial (seconds)",
            min_value=10,
            max_value=3600,
            value=current_timeout,
            help="Maximum time allowed per trial"
        )
        SessionState.update_configuration('timeout_per_trial', timeout)

def render_validation_config():
    """Render validation configuration section"""
    st.subheader("Validation Tests")

    st.write("Select which validation tests to run after optimization:")

    validation_options = [
        ("permutation", "Permutation Test", "Test if results are due to chance"),
        ("monte_carlo", "Monte Carlo Simulation", "Simulate different market scenarios"),
        ("walk_forward", "Walk-Forward Analysis", "Test on sequential time periods"),
        ("regime_detection", "Regime Detection", "Test across different market regimes"),
        ("noise_injection", "Noise Injection", "Test robustness to data noise")
    ]

    selected_tests = []
    for test_id, test_name, test_desc in validation_options:
        if st.checkbox(test_name, help=test_desc):
            selected_tests.append(test_id)

    # Store as comma-separated string
    validation_tests = ','.join(selected_tests) if selected_tests else None
    SessionState.update_configuration('validation_tests', validation_tests)

def render_config_actions():
    """Render configuration action buttons"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 Save Configuration", use_container_width=True):
            save_current_config()

    with col2:
        if st.button("📂 Load Configuration", use_container_width=True):
            load_config_dialog()

    with col3:
        if st.button("✓ Validate", use_container_width=True):
            validate_current_config()

    with col4:
        if st.button("🗑 Clear", use_container_width=True):
            SessionState.reset()
            st.success("Configuration cleared")
            st.rerun()

def save_current_config():
    """Save current configuration as a template"""
    config = SessionState.get_configuration()

    if not config:
        st.warning("No configuration to save")
        return

    # Simple save dialog
    with st.form("save_config_form"):
        template_name = st.text_input("Template Name", placeholder="e.g., ES_5m_Standard")
        submitted = st.form_submit_button("Save Template")

        if submitted and template_name:
            SessionState.save_template(template_name, config)
            st.success(f"Configuration saved as '{template_name}'")

def load_config_dialog():
    """Load configuration from templates"""
    templates = SessionState.get_all_templates()

    if not templates:
        st.info("No saved templates available")
        return

    template_name = st.selectbox("Select Template", options=list(templates.keys()))

    if st.button("Load Selected Template"):
        config = SessionState.load_template(template_name)
        if config:
            SessionState.save_configuration(config)
            st.success(f"Loaded template '{template_name}'")
            st.rerun()

def validate_current_config():
    """Validate the current configuration"""
    config = SessionState.get_configuration()

    if not config:
        st.warning("No configuration to validate")
        return

    is_valid, errors = ConfigurationValidator.validate(config)

    if is_valid:
        st.success("Configuration is valid!")
    else:
        st.error("Configuration has errors:")
        for error in errors:
            st.markdown(f"- {error}")
