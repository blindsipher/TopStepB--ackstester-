"""
Quick verification that Numba integration is working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from TopStepB.strategies.bollinger_squeeze import strategy as strat_module
from TopStepB.strategies.bollinger_squeeze.numba_position_manager import NUMBA_AVAILABLE

print("="*70)
print("NUMBA INTEGRATION VERIFICATION")
print("="*70)

print(f"\nNumba available: {NUMBA_AVAILABLE}")
print(f"USE_NUMBA_POSITION_MANAGEMENT flag: {strat_module.USE_NUMBA_POSITION_MANAGEMENT}")

if NUMBA_AVAILABLE and strat_module.USE_NUMBA_POSITION_MANAGEMENT:
    print("\n✅ SUCCESS: Numba optimization is ACTIVE")
    print("   Strategy will use JIT-compiled position management")
elif NUMBA_AVAILABLE and not strat_module.USE_NUMBA_POSITION_MANAGEMENT:
    print("\n⚠️  WARNING: Numba is available but disabled")
    print("   Set USE_NUMBA_POSITION_MANAGEMENT = True to enable")
elif not NUMBA_AVAILABLE:
    print("\n⚠️  WARNING: Numba is not installed")
    print("   Install with: pip install numba")
    print("   Strategy will use fallback Python implementation")

print("\n" + "="*70)
