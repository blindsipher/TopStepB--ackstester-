"""
Results Dashboard Component
Display optimization results and performance metrics
"""
import streamlit as st
import plotly.graph_objects as go
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService
from src.ui.utils.session_state import SessionState

def render():
    """Render the results dashboard"""
    st.header("Optimization Results")

    # Study selection
    db = DatabaseService()
    studies = db.list_studies(limit=50)

    if not studies:
        st.info("No optimization studies found")
        st.write("Run an optimization first to see results here")
        return

    study_names = [s['study_name'] for s in studies]
    selected_study = st.selectbox("Select Study", options=study_names)

    if not selected_study:
        return

    # Get study data
    trials_df = db.get_study_trials(selected_study)
    best_trial = db.get_best_trial(selected_study)

    if trials_df.empty:
        st.warning("No trials found for this study")
        return

    # Best trial metrics
    st.subheader("Best Trial")
    if best_trial:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Trial Number", best_trial['number'])
        with col2:
            st.metric("Best Score", f"{best_trial['value']:.4f}")
        with col3:
            st.metric("Status", best_trial['state'])
        with col4:
            if best_trial['datetime_complete']:
                st.metric("Completed", best_trial['datetime_complete'].strftime("%Y-%m-%d %H:%M"))

    # Trial history chart
    st.subheader("Trial History")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trials_df['number'],
        y=trials_df['value'],
        mode='markers+lines',
        name='Trial Score'
    ))
    fig.update_layout(
        title="Optimization Progress",
        xaxis_title="Trial Number",
        yaxis_title="Score",
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Trial summary stats
    st.subheader("Trial Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Trials", len(trials_df))
    with col2:
        completed = len(trials_df[trials_df['state'] == 'COMPLETE'])
        st.metric("Completed", completed)
    with col3:
        if not trials_df['value'].isna().all():
            st.metric("Mean Score", f"{trials_df['value'].mean():.4f}")

    # Trials table
    st.subheader("All Trials")
    st.dataframe(trials_df, use_container_width=True)

    # Export options
    st.markdown("---")
    if st.button("📥 Export Results to CSV"):
        csv = trials_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{selected_study}_results.csv",
            mime="text/csv"
        )
