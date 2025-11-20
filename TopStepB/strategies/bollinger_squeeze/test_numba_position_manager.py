"""
Tests and Benchmarks for Numba Position Management

Validates correctness and measures performance improvement.
"""

import pytest
import pandas as pd
import numpy as np
import time
from typing import Dict, Any

# Import both implementations
from .numba_position_manager import (
    apply_position_management_wrapper,
    NUMBA_AVAILABLE,
    get_exit_method_code,
)
from .strategy import BollingerSqueezeStrategy
from .parameters import get_default_parameters
from .indicators import calculate_all_indicators


class TestNumbaPositionManager:
    """Test suite for Numba position management."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        n = 1000

        # Generate realistic price data
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.random.rand(n) * 2
        low = close - np.random.rand(n) * 2
        open_ = close + (np.random.rand(n) - 0.5)
        volume = np.random.randint(1000, 10000, n)

        df = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=pd.date_range('2023-01-01', periods=n, freq='5min'))

        return df

    @pytest.fixture
    def sample_indicators(self, sample_data):
        """Generate indicators for sample data."""
        params = get_default_parameters()
        return calculate_all_indicators(sample_data, params, use_gpu=None)

    @pytest.fixture
    def sample_entry_signals(self, sample_data):
        """Create sample entry signals."""
        signals = pd.Series(0, index=sample_data.index, dtype=np.int8)

        # Add some long entries
        signals.iloc[100] = 1
        signals.iloc[300] = 1
        signals.iloc[500] = 1

        # Add some short entries
        signals.iloc[200] = -1
        signals.iloc[400] = -1
        signals.iloc[600] = -1

        return signals

    def test_exit_method_code_conversion(self):
        """Test exit method string to code conversion."""
        assert get_exit_method_code('fixed_rr') == 0
        assert get_exit_method_code('trailing_donchian') == 1
        assert get_exit_method_code('opposite_band') == 2
        assert get_exit_method_code('invalid') == 1  # Default

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_numba_vs_original_fixed_rr(self, sample_data, sample_indicators, sample_entry_signals):
        """Test Numba implementation matches original for fixed_rr exit."""
        params = get_default_parameters()
        params['exit_method'] = 'fixed_rr'

        # Get Numba result
        numba_signals = apply_position_management_wrapper(
            sample_data, sample_entry_signals, sample_indicators, params
        )

        # Get original result
        strategy = BollingerSqueezeStrategy()

        # Temporarily disable Numba to get original implementation
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module
        original_flag = strat_module.USE_NUMBA_POSITION_MANAGEMENT
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False

        try:
            original_signals = strategy._apply_stateful_position_management(
                sample_data, sample_entry_signals, sample_indicators, params
            )
        finally:
            strat_module.USE_NUMBA_POSITION_MANAGEMENT = original_flag

        # Compare results
        np.testing.assert_array_equal(
            numba_signals.values,
            original_signals.values,
            err_msg="Numba and original implementation produce different results for fixed_rr"
        )

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_numba_vs_original_trailing_donchian(self, sample_data, sample_indicators, sample_entry_signals):
        """Test Numba implementation matches original for trailing_donchian exit."""
        params = get_default_parameters()
        params['exit_method'] = 'trailing_donchian'

        # Get Numba result
        numba_signals = apply_position_management_wrapper(
            sample_data, sample_entry_signals, sample_indicators, params
        )

        # Get original result
        strategy = BollingerSqueezeStrategy()

        # Temporarily disable Numba
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module
        original_flag = strat_module.USE_NUMBA_POSITION_MANAGEMENT
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False

        try:
            original_signals = strategy._apply_stateful_position_management(
                sample_data, sample_entry_signals, sample_indicators, params
            )
        finally:
            strat_module.USE_NUMBA_POSITION_MANAGEMENT = original_flag

        # Compare results
        np.testing.assert_array_equal(
            numba_signals.values,
            original_signals.values,
            err_msg="Numba and original implementation produce different results for trailing_donchian"
        )

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_numba_vs_original_opposite_band(self, sample_data, sample_indicators, sample_entry_signals):
        """Test Numba implementation matches original for opposite_band exit."""
        params = get_default_parameters()
        params['exit_method'] = 'opposite_band'

        # Get Numba result
        numba_signals = apply_position_management_wrapper(
            sample_data, sample_entry_signals, sample_indicators, params
        )

        # Get original result
        strategy = BollingerSqueezeStrategy()

        # Temporarily disable Numba
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module
        original_flag = strat_module.USE_NUMBA_POSITION_MANAGEMENT
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False

        try:
            original_signals = strategy._apply_stateful_position_management(
                sample_data, sample_entry_signals, sample_indicators, params
            )
        finally:
            strat_module.USE_NUMBA_POSITION_MANAGEMENT = original_flag

        # Compare results
        np.testing.assert_array_equal(
            numba_signals.values,
            original_signals.values,
            err_msg="Numba and original implementation produce different results for opposite_band"
        )

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_stop_loss_logic(self, sample_data, sample_indicators):
        """Test that stop-loss logic works correctly."""
        params = get_default_parameters()
        params['exit_method'] = 'fixed_rr'
        params['stop_loss_atr_multiplier'] = 2.0

        # Create entry signal that should trigger stop-loss
        signals = pd.Series(0, index=sample_data.index, dtype=np.int8)
        signals.iloc[100] = 1  # Long entry

        result = apply_position_management_wrapper(
            sample_data, signals, sample_indicators, params
        )

        # Check that position is opened at signal
        assert result.iloc[100] == 0  # Not in position yet (entry at bar i-1)
        assert result.iloc[101] == 1  # Position opened (entry at bar i)

        # Find where position exits
        exit_idx = None
        for i in range(102, len(result)):
            if result.iloc[i] == 0:
                exit_idx = i
                break

        # Should exit at some point (either stop or target)
        assert exit_idx is not None, "Position should exit at some point"

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_position_alternation(self, sample_data, sample_indicators):
        """Test that positions can alternate between long and short."""
        params = get_default_parameters()
        params['exit_method'] = 'fixed_rr'

        # Create alternating signals
        signals = pd.Series(0, index=sample_data.index, dtype=np.int8)
        signals.iloc[100] = 1   # Long
        signals.iloc[300] = -1  # Short
        signals.iloc[500] = 1   # Long again

        result = apply_position_management_wrapper(
            sample_data, signals, sample_indicators, params
        )

        # Check that we see both 1 and -1 in results
        assert 1 in result.values, "Should have long positions"
        assert -1 in result.values, "Should have short positions"

    @pytest.mark.benchmark
    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_benchmark_numba_vs_original(self, sample_data, sample_indicators, sample_entry_signals):
        """Benchmark performance: Numba vs Original implementation."""
        params = get_default_parameters()
        params['exit_method'] = 'trailing_donchian'

        strategy = BollingerSqueezeStrategy()
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module

        # Benchmark Numba version
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True
        numba_times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = strategy._apply_stateful_position_management(
                sample_data, sample_entry_signals, sample_indicators, params
            )
            numba_times.append(time.perf_counter() - start)

        numba_avg = np.mean(numba_times)

        # Benchmark original version
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
        original_times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = strategy._apply_stateful_position_management(
                sample_data, sample_entry_signals, sample_indicators, params
            )
            original_times.append(time.perf_counter() - start)

        original_avg = np.mean(original_times)

        # Restore flag
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

        # Calculate speedup
        speedup = original_avg / numba_avg

        print(f"\n{'='*60}")
        print(f"PERFORMANCE BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"Data size: {len(sample_data)} bars")
        print(f"\nOriginal Python:")
        print(f"  Average: {original_avg*1000:.2f}ms")
        print(f"  Min:     {min(original_times)*1000:.2f}ms")
        print(f"  Max:     {max(original_times)*1000:.2f}ms")
        print(f"\nNumba JIT:")
        print(f"  Average: {numba_avg*1000:.2f}ms")
        print(f"  Min:     {min(numba_times)*1000:.2f}ms")
        print(f"  Max:     {max(numba_times)*1000:.2f}ms")
        print(f"\nSpeedup: {speedup:.2f}x faster")
        print(f"{'='*60}\n")

        # Assert significant speedup
        assert speedup > 2.0, f"Expected >2x speedup, got {speedup:.2f}x"


class TestIntegration:
    """Integration tests with full strategy."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for integration testing."""
        np.random.seed(42)
        n = 500

        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.random.rand(n) * 2
        low = close - np.random.rand(n) * 2
        open_ = close + (np.random.rand(n) - 0.5)
        volume = np.random.randint(1000, 10000, n)

        df = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=pd.date_range('2023-01-01', periods=n, freq='5min'))

        return df

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_full_strategy_with_numba(self, sample_data):
        """Test full strategy execution with Numba enabled."""
        from config.system_config import TradingConfig

        strategy = BollingerSqueezeStrategy()
        params = get_default_parameters()

        config = TradingConfig(
            symbol="ES",
            tick_size=0.25,
            point_value=50,
            initial_capital=100000,
            contracts_per_trade=1,
        )

        # Should not raise any errors
        signals = strategy.generate_signals(sample_data, params, config)

        # Basic validation
        assert len(signals) == len(sample_data)
        assert signals.dtype == np.int8
        assert all(s in [-1, 0, 1] for s in signals.unique())

    @pytest.mark.skipif(not NUMBA_AVAILABLE, reason="Numba not available")
    def test_strategy_determinism(self, sample_data):
        """Test that strategy produces deterministic results."""
        from config.system_config import TradingConfig

        strategy = BollingerSqueezeStrategy()
        params = get_default_parameters()

        config = TradingConfig(
            symbol="ES",
            tick_size=0.25,
            point_value=50,
            initial_capital=100000,
            contracts_per_trade=1,
        )

        # Run twice
        signals1 = strategy.generate_signals(sample_data, params, config)
        strategy.reset_state()
        signals2 = strategy.generate_signals(sample_data, params, config)

        # Should be identical
        np.testing.assert_array_equal(
            signals1.values,
            signals2.values,
            err_msg="Strategy should produce deterministic results"
        )


def run_comprehensive_benchmark():
    """
    Standalone function to run comprehensive benchmarks.
    Can be called directly for detailed performance analysis.
    """
    if not NUMBA_AVAILABLE:
        print("Numba not available - skipping benchmarks")
        return

    print("\n" + "="*70)
    print("COMPREHENSIVE PERFORMANCE BENCHMARK")
    print("="*70)

    # Generate test data of various sizes
    sizes = [500, 1000, 2000, 5000]

    for n in sizes:
        print(f"\nTesting with {n} bars...")

        # Generate data
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.random.rand(n) * 2
        low = close - np.random.rand(n) * 2
        open_ = close + (np.random.rand(n) - 0.5)
        volume = np.random.randint(1000, 10000, n)

        data = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=pd.date_range('2023-01-01', periods=n, freq='5min'))

        # Generate indicators and signals
        params = get_default_parameters()
        indicators = calculate_all_indicators(data, params, use_gpu=None)

        signals = pd.Series(0, index=data.index, dtype=np.int8)
        signals.iloc[100] = 1
        if n > 300:
            signals.iloc[300] = -1
        if n > 500:
            signals.iloc[500] = 1

        # Benchmark
        strategy = BollingerSqueezeStrategy()
        import TopStepB.strategies.bollinger_squeeze.strategy as strat_module

        # Numba version
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True
        start = time.perf_counter()
        for _ in range(5):
            _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
        numba_time = (time.perf_counter() - start) / 5

        # Original version
        strat_module.USE_NUMBA_POSITION_MANAGEMENT = False
        start = time.perf_counter()
        for _ in range(5):
            _ = strategy._apply_stateful_position_management(data, signals, indicators, params)
        original_time = (time.perf_counter() - start) / 5

        strat_module.USE_NUMBA_POSITION_MANAGEMENT = True

        speedup = original_time / numba_time

        print(f"  Original: {original_time*1000:.2f}ms")
        print(f"  Numba:    {numba_time*1000:.2f}ms")
        print(f"  Speedup:  {speedup:.2f}x")

    print("\n" + "="*70)


if __name__ == '__main__':
    # Run comprehensive benchmarks when executed directly
    run_comprehensive_benchmark()
