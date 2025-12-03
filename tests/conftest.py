import sys
import pathlib

# Ensure the core project package is importable
PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "TopStepB"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
