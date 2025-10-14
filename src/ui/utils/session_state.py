"""
Session State Management for Streamlit UI
Handles persistent state across page reloads and navigation
"""
import streamlit as st
from typing import Any, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

class SessionState:
    """Manage UI session state across reruns"""

    @staticmethod
    def initialize():
        """Initialize session state variables"""

        # Configuration state
        if 'configuration' not in st.session_state:
            st.session_state.configuration = {}

        # Current optimization
        if 'current_optimization' not in st.session_state:
            st.session_state.current_optimization = None

        # Optimization history
        if 'optimization_history' not in st.session_state:
            st.session_state.optimization_history = []

        # Data source
        if 'data_file' not in st.session_state:
            st.session_state.data_file = None

        if 'synthetic_bars' not in st.session_state:
            st.session_state.synthetic_bars = None

        # Configuration templates
        if 'config_templates' not in st.session_state:
            st.session_state.config_templates = {}

        # Results cache
        if 'results_cache' not in st.session_state:
            st.session_state.results_cache = {}

        # Last update timestamp
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()

        # UI preferences
        if 'ui_preferences' not in st.session_state:
            st.session_state.ui_preferences = {
                'auto_refresh': True,
                'refresh_interval': 5,
                'show_advanced': False
            }

    @staticmethod
    def save_configuration(config: Dict[str, Any]):
        """Save configuration to session"""
        st.session_state.configuration = config
        st.session_state.last_update = datetime.now()

    @staticmethod
    def get_configuration() -> Dict[str, Any]:
        """Get current configuration"""
        return st.session_state.get('configuration', {})

    @staticmethod
    def update_configuration(key: str, value: Any):
        """Update a single configuration value"""
        if 'configuration' not in st.session_state:
            st.session_state.configuration = {}
        st.session_state.configuration[key] = value
        st.session_state.last_update = datetime.now()

    @staticmethod
    def set_current_optimization(study_name: str):
        """Set the current running optimization"""
        st.session_state.current_optimization = study_name
        if study_name not in st.session_state.optimization_history:
            st.session_state.optimization_history.append(study_name)

    @staticmethod
    def get_current_optimization() -> Optional[str]:
        """Get current optimization study name"""
        return st.session_state.get('current_optimization')

    @staticmethod
    def clear_current_optimization():
        """Clear current optimization"""
        st.session_state.current_optimization = None

    @staticmethod
    def set_data_source(data_file: Optional[str] = None, synthetic_bars: Optional[int] = None):
        """Set the data source"""
        st.session_state.data_file = data_file
        st.session_state.synthetic_bars = synthetic_bars

    @staticmethod
    def get_data_source() -> tuple:
        """Get current data source"""
        return (st.session_state.get('data_file'), st.session_state.get('synthetic_bars'))

    @staticmethod
    def _get_templates_dir() -> Path:
        """Get the directory for configuration templates"""
        templates_dir = Path.home() / ".topstep_backtester" / "config_templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        return templates_dir

    @staticmethod
    def save_template(name: str, config: Dict[str, Any]) -> bool:
        """Save a configuration template to disk"""
        try:
            templates_dir = SessionState._get_templates_dir()
            template_file = templates_dir / f"{name}.json"

            with open(template_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)

            # Also update session state cache
            if 'config_templates' not in st.session_state:
                st.session_state.config_templates = {}
            st.session_state.config_templates[name] = config

            return True
        except Exception as e:
            print(f"Error saving template: {e}")
            return False

    @staticmethod
    def load_template(name: str) -> Optional[Dict[str, Any]]:
        """Load a configuration template from disk"""
        try:
            templates_dir = SessionState._get_templates_dir()
            template_file = templates_dir / f"{name}.json"

            if not template_file.exists():
                return None

            with open(template_file, 'r') as f:
                config = json.load(f)

            return config
        except Exception as e:
            print(f"Error loading template: {e}")
            return None

    @staticmethod
    def get_all_templates() -> Dict[str, Dict[str, Any]]:
        """Get all saved templates from disk"""
        try:
            templates_dir = SessionState._get_templates_dir()
            templates = {}

            for template_file in templates_dir.glob("*.json"):
                name = template_file.stem
                try:
                    with open(template_file, 'r') as f:
                        templates[name] = json.load(f)
                except Exception as e:
                    print(f"Error loading template {name}: {e}")
                    continue

            return templates
        except Exception as e:
            print(f"Error getting templates: {e}")
            return {}

    @staticmethod
    def delete_template(name: str) -> bool:
        """Delete a configuration template"""
        try:
            templates_dir = SessionState._get_templates_dir()
            template_file = templates_dir / f"{name}.json"

            if template_file.exists():
                template_file.unlink()

            # Also remove from session state cache
            if 'config_templates' in st.session_state and name in st.session_state.config_templates:
                del st.session_state.config_templates[name]

            return True
        except Exception as e:
            print(f"Error deleting template: {e}")
            return False

    @staticmethod
    def cache_results(study_name: str, results: Dict[str, Any]):
        """Cache optimization results"""
        if 'results_cache' not in st.session_state:
            st.session_state.results_cache = {}
        st.session_state.results_cache[study_name] = results

    @staticmethod
    def get_cached_results(study_name: str) -> Optional[Dict[str, Any]]:
        """Get cached results"""
        return st.session_state.get('results_cache', {}).get(study_name)

    @staticmethod
    def clear_cache():
        """Clear results cache"""
        st.session_state.results_cache = {}

    @staticmethod
    def set_preference(key: str, value: Any):
        """Set a UI preference"""
        if 'ui_preferences' not in st.session_state:
            st.session_state.ui_preferences = {}
        st.session_state.ui_preferences[key] = value

    @staticmethod
    def get_preference(key: str, default: Any = None) -> Any:
        """Get a UI preference"""
        return st.session_state.get('ui_preferences', {}).get(key, default)

    @staticmethod
    def reset():
        """Reset all session state"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        SessionState.initialize()
