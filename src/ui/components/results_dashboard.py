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

    # Check if a study was pre-selected from History page
    default_index = 0
    if 'selected_study' in st.session_state and st.session_state.selected_study in study_names:
        default_index = study_names.index(st.session_state.selected_study)

    selected_study = st.selectbox("Select Study", options=study_names, index=default_index)

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
            if best_trial['value'] is not None:
                st.metric("Best Score", f"{best_trial['value']:.4f}")
            else:
                st.metric("Best Score", "N/A")
        with col3:
            st.metric("Status", best_trial['state'])
        with col4:
            if best_trial['datetime_complete']:
                st.metric("Completed", best_trial['datetime_complete'].strftime("%Y-%m-%d %H:%M"))

        # Display best trial parameters
        with st.expander("View Best Trial Parameters", expanded=False):
            params = {}
            if 'number' not in best_trial:
                st.warning("Trial number not available")
            else:
                try:
                    params = db.get_trial_parameters(selected_study, best_trial['number'])
                except Exception as e:
                    st.error(f"Error loading trial parameters: {str(e)}")
                    params = {}

            if params:
                def format_param_value(value):
                    if value is None:
                        return "N/A"
                    elif isinstance(value, bool):
                        return str(value)
                    elif isinstance(value, float):
                        return f"{value:.4f}"
                    elif isinstance(value, int):
                        return str(value)
                    elif isinstance(value, (list, dict)):
                        str_val = str(value)
                        return str_val[:50] + "..." if len(str_val) > 50 else str_val
                    else:
                        return str(value)

                # Categorize parameters with priority order to avoid overlaps
                categorized_keys = set()

                bollinger_params = {}
                for k, v in params.items():
                    if 'bb_' in k.lower():
                        bollinger_params[k] = v
                        categorized_keys.add(k)

                keltner_params = {}
                for k, v in params.items():
                    if k not in categorized_keys and 'kc_' in k.lower():
                        keltner_params[k] = v
                        categorized_keys.add(k)

                exit_params = {}
                for k, v in params.items():
                    if k not in categorized_keys and 'exit' in k.lower():
                        exit_params[k] = v
                        categorized_keys.add(k)

                filter_params = {}
                for k, v in params.items():
                    if k not in categorized_keys and 'filter' in k.lower():
                        filter_params[k] = v
                        categorized_keys.add(k)

                risk_params = {}
                for k, v in params.items():
                    if k not in categorized_keys and any(x in k.lower() for x in ['stop', 'risk', 'atr', 'target']):
                        risk_params[k] = v
                        categorized_keys.add(k)

                other_params = {k: v for k, v in params.items() if k not in categorized_keys}

                col1, col2 = st.columns(2)

                with col1:
                    if bollinger_params:
                        st.write("**Bollinger Bands**")
                        for k, v in bollinger_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")

                    if keltner_params:
                        st.write("**Keltner Channels**")
                        for k, v in keltner_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")

                    if filter_params:
                        st.write("**Filters**")
                        for k, v in filter_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")

                with col2:
                    if risk_params:
                        st.write("**Risk Management**")
                        for k, v in risk_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")

                    if exit_params:
                        st.write("**Exit Rules**")
                        for k, v in exit_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")

                    if other_params:
                        st.write("**Other Parameters**")
                        for k, v in other_params.items():
                            st.write(f"{k}: `{format_param_value(v)}`")
            else:
                st.info("No parameters found for this trial")

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
    if st.button("Export Results to CSV"):
        csv = trials_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{selected_study}_results.csv",
            mime="text/csv"
        )
