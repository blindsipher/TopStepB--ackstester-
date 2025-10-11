"""
Data Loader Component
Upload and validate data files for backtesting
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.session_state import SessionState
from src.ui.utils.validators import DataValidator

def render():
    """Render the data loader page"""
    st.header("Data Source Configuration")

    # Data source tabs
    tab1, tab2 = st.tabs(["Upload File", "Synthetic Data"])

    with tab1:
        render_file_upload()

    with tab2:
        render_synthetic_data()

    # Show current data source
    st.markdown("---")
    display_current_data_source()

def render_file_upload():
    """Render file upload section"""
    st.subheader("Upload Data File")

    st.info("Upload a CSV or Parquet file with OHLCV data")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'parquet'],
        help="File must contain: datetime, open, high, low, close, volume"
    )

    if uploaded_file is not None:
        try:
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.parquet'):
                df = pd.read_parquet(uploaded_file)
            else:
                st.error("Unsupported file type")
                return

            # Validate
            is_valid, errors = DataValidator.validate_dataframe(df)

            if is_valid:
                # Save to temp location
                temp_path = save_uploaded_file(uploaded_file)

                # Store in session
                SessionState.set_data_source(data_file=temp_path, synthetic_bars=None)

                st.success(f"File loaded successfully: {len(df)} rows")

                # Show preview
                with st.expander("Data Preview"):
                    st.dataframe(df.head(10))
                    st.write(f"**Shape**: {df.shape}")
                    st.write(f"**Columns**: {list(df.columns)}")

            else:
                st.error("File validation failed:")
                for error in errors:
                    st.markdown(f"- {error}")

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

def render_synthetic_data():
    """Render synthetic data configuration"""
    st.subheader("Generate Synthetic Data")

    st.info("Generate synthetic price data for testing")

    bars = st.number_input(
        "Number of Bars",
        min_value=100,
        max_value=50000,
        value=5000,
        step=100,
        help="Number of synthetic price bars to generate"
    )

    symbol = st.selectbox(
        "Symbol (for price ranges)",
        options=['ES', 'NQ', 'YM', 'CL', 'GC'],
        help="Symbol determines realistic price levels"
    )

    if st.button("Generate Synthetic Data"):
        SessionState.set_data_source(data_file=None, synthetic_bars=int(bars))
        st.success(f"Configured to generate {bars} synthetic bars for {symbol}")

def display_current_data_source():
    """Display currently configured data source"""
    st.subheader("Current Data Source")

    data_file, synthetic_bars = SessionState.get_data_source()

    if data_file:
        st.info(f"📁 **Data File**: {data_file}")
        if st.button("Clear Data File"):
            SessionState.set_data_source(data_file=None, synthetic_bars=None)
            st.rerun()
    elif synthetic_bars:
        st.info(f"🎲 **Synthetic Data**: {synthetic_bars} bars")
        if st.button("Clear Synthetic Data"):
            SessionState.set_data_source(data_file=None, synthetic_bars=None)
            st.rerun()
    else:
        st.warning("No data source configured")

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp directory"""
    temp_dir = Path.home() / ".topstep_ui_temp"
    temp_dir.mkdir(exist_ok=True)

    file_path = temp_dir / uploaded_file.name

    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    return str(file_path)
