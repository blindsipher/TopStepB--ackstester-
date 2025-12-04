"""
Quick test to verify UI imports work
"""
import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Check if UI modules exist
try:
    import importlib.util
    ui_modules_exist = all([
        importlib.util.find_spec('src.ui.utils.session_state'),
        importlib.util.find_spec('src.ui.utils.validators'),
        importlib.util.find_spec('src.ui.utils.formatters'),
        importlib.util.find_spec('src.ui.services.database_service'),
        importlib.util.find_spec('src.ui.services.pipeline_service'),
    ])
except (ImportError, ValueError, AttributeError):
    ui_modules_exist = False

# Skip all tests if UI modules don't exist
pytestmark = pytest.mark.skipif(
    not ui_modules_exist,
    reason="UI modules (src/ui) not found in project"
)


def test_session_state_import():
    """Test that session_state module imports successfully."""
    from src.ui.utils.session_state import SessionState
    assert SessionState is not None


def test_validators_import():
    """Test that validators module imports successfully."""
    from src.ui.utils.validators import ConfigurationValidator
    assert ConfigurationValidator is not None


def test_formatters_import():
    """Test that formatters module imports successfully."""
    from src.ui.utils.formatters import NumberFormatter
    assert NumberFormatter is not None


def test_database_service_import():
    """Test that database_service module imports successfully."""
    from src.ui.services.database_service import DatabaseService
    assert DatabaseService is not None


def test_pipeline_service_import():
    """Test that pipeline_service module imports successfully."""
    from src.ui.services.pipeline_service import PipelineService
    assert PipelineService is not None


def test_all_ui_imports():
    """Test that all UI imports work together."""
    # Import all at once to verify no conflicts
    from src.ui.utils.session_state import SessionState
    from src.ui.utils.validators import ConfigurationValidator
    from src.ui.utils.formatters import NumberFormatter
    from src.ui.services.database_service import DatabaseService
    from src.ui.services.pipeline_service import PipelineService

    # Verify all imports succeeded
    assert SessionState is not None
    assert ConfigurationValidator is not None
    assert NumberFormatter is not None
    assert DatabaseService is not None
    assert PipelineService is not None
