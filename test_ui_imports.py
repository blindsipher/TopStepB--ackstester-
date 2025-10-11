"""
Quick test to verify UI imports work
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing UI imports...")

try:
    print("1. Testing session_state...")
    from src.ui.utils.session_state import SessionState
    print("   [OK] session_state")

    print("2. Testing validators...")
    from src.ui.utils.validators import ConfigurationValidator
    print("   [OK] validators")

    print("3. Testing formatters...")
    from src.ui.utils.formatters import NumberFormatter
    print("   [OK] formatters")

    print("4. Testing database_service...")
    from src.ui.services.database_service import DatabaseService
    print("   [OK] database_service")

    print("5. Testing pipeline_service...")
    from src.ui.services.pipeline_service import PipelineService
    print("   [OK] pipeline_service")

    print("\nAll imports successful!")
    print("\nUI is ready to launch with: python -m streamlit run src/ui/app.py")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
