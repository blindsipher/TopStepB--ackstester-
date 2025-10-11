"""
Optimization Monitor Component
Real-time monitoring of running optimizations
"""
import streamlit as st
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.session_state import SessionState
from src.ui.services.database_service import DatabaseService

def render():
    """Render the optimization monitor page"""
    st.header("Optimization Monitor")

    current_optimization = SessionState.get_current_optimization()

    if not current_optimization:
        st.info("No optimization currently running")
        st.write("Configure and launch an optimization from the 'Run Optimization' page")
        return

    st.subheader(f"Monitoring: {current_optimization}")

    # Get progress from database
    db = DatabaseService()
    progress = db.get_study_progress(current_optimization)

    if progress:
        # Progress metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Trials", progress['total_trials'])
        with col2:
            st.metric("Completed", progress['completed_trials'])
        with col3:
            st.metric("Running", progress['running_trials'])
        with col4:
            best_value = progress['best_value']
            st.metric("Best Score", f"{best_value:.4f}" if best_value else "N/A")

        # Progress bar
        if progress['total_trials'] > 0:
            progress_pct = progress['completed_trials'] / progress['total_trials']
            st.progress(progress_pct)

        # Recent trials
        st.subheader("Recent Trials")
        trials_df = db.get_study_trials(current_optimization)
        if not trials_df.empty:
            st.dataframe(trials_df.head(20), use_container_width=True)
        else:
            st.info("No trials yet")

    else:
        st.warning("No data available for this study")

    # Control buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("⏹ Stop Optimization", use_container_width=True):
            SessionState.clear_current_optimization()
            st.success("Optimization stopped")
            st.rerun()

    with col3:
        if st.button("📊 View Results", use_container_width=True):
            st.switch_page("Results")

    # Auto-refresh option
    if st.checkbox("Auto-refresh (every 5s)"):
        time.sleep(5)
        st.rerun()
