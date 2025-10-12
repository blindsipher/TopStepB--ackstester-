"""
Study Browser Component
Browse and manage historical optimization studies
"""
import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService

def render():
    """Render the study browser page"""
    st.header("Study History")

    db = DatabaseService()
    studies = db.list_studies(limit=100)

    if not studies:
        st.info("No studies found in database")
        st.write("Run some optimizations first to see them here")
        return

    st.write(f"Found {len(studies)} studies")

    # Studies table
    for study in studies:
        with st.expander(f"📊 {study['study_name']}"):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**Study ID**: {study['study_id']}")
                st.write(f"**Study Name**: {study['study_name']}")

            with col2:
                if st.button("View Results", key=f"view_{study['study_id']}"):
                    st.session_state.selected_study = study['study_name']
                    st.info("Navigate to 'Results' page in the sidebar to view this study")
                    st.rerun()

            with col3:
                if st.button("Delete", key=f"delete_{study['study_id']}", type="secondary"):
                    if db.delete_study(study['study_name']):
                        st.success(f"Deleted {study['study_name']}")
                        st.rerun()
                    else:
                        st.error("Failed to delete study")

    # Bulk operations
    st.markdown("---")
    st.subheader("Bulk Operations")
    if st.button("🗑 Clear All Studies", type="secondary"):
        if st.checkbox("I understand this will delete all studies"):
            for study in studies:
                db.delete_study(study['study_name'])
            st.success("All studies deleted")
            st.rerun()
