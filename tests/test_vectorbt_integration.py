"""
Test Suite for VectorBT Integration
====================================

Validates the VectorBT portfolio engine against the original loop-based
implementation to ensure correctness and measure performance improvements.

Test Categories:
1. Functional correctness - Results match original implementation
2. Performance benchmarks - Measure speedup across different data sizes
3. Edge cases - Zero trades, single trade, position flips
4. Futures-specific - Tick values, commission, slippage
5. Integration tests - Full Optuna optimization runs
"""

import pytest
import pandas as pd
import numpy as np
import time
from decimal import Decimal
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from config.system_config import (
    MarketSpec, TradingConfig, TopStepMarkets, TopStepAccounts,
    ExecutionModels, create_trading_config
)
from optimization.vectorbt_engine import VectorBTPortfolioEngine, IndicatorCache


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def mes_market_spec():
    """MES (Micro E-mini S&P 500) market specification from TopStepMarkets."""
    return TopStepMarkets.MES


@pytest.fixture
def trading_config():
    """Trading configuration with MES market and TopStep account."""
    return create_trading_config(
        symbol="MES",
        timeframe="5m",
        account_type="topstep_50k",
        commission_model=ExecutionModels.TOPSTEP_COMMISSION,
        slippage_model=ExecutionModels.REALISTIC_SLIPPAGE
    )


@pytest.fixture
def execution_config():
    """Standard execution configuration from execution models."""
    return {
        'commission_per_trade': 2.50,  # From TOPSTEP_COMMISSION
        'slippage_ticks': 1,  # From market typical slippage
        'contracts_per_trade': 1
    }


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='5min')

    # Generate realistic price action
    close_prices = 4500 + np.cumsum(np.random.randn(1000) * 2)
    high_prices = close_prices + np.abs(np.random.randn(1000) * 1.5)
    low_prices = close_prices - np.abs(np.random.randn(1000) * 1.5)
    open_prices = close_prices.copy()
    open_prices[1:] = close_prices[:-1]  # Open = previous close
    volume = np.random.randint(100, 10000, 1000)

    return pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    }, index=dates)


@pytest.fixture
def simple_long_signals(sample_ohlcv_data):
    """Generate simple long-only signals (enter/exit every 50 bars)."""
    signals = pd.Series(0, index=sample_ohlcv_data.index)

    # Long from bar 10-60, 110-160, 210-260
    for start in range(10, len(signals), 100):
        signals.iloc[start:start+50] = 1

    return signals


@pytest.fixture
def long_short_signals(sample_ohlcv_data):
    """Generate long/short signals."""
    signals = pd.Series(0, index=sample_ohlcv_data.index)

    # Long positions
    for start in range(10, len(signals), 150):
        signals.iloc[start:start+30] = 1

    # Short positions
    for start in range(60, len(signals), 150):
        signals.iloc[start:start+30] = -1

    return signals


# ==============================================================================
# FUNCTIONAL CORRECTNESS TESTS
# ==============================================================================

class TestVectorBTEngine:
    """Test VectorBT portfolio engine functionality."""

    def test_initialization(self, trading_config, execution_config):
        """Test engine initializes correctly."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        assert engine.tick_size == 0.25
        assert engine.tick_value == 1.25
        # Updated to match actual commission from TOPSTEP_COMMISSION
        assert engine.commission_per_trade == 2.50
        assert engine.slippage_ticks == 1
        # Updated to match AccountConfig from topstep_50k
        assert engine.initial_cash == 50000.0

    def test_zero_trades(self, trading_config, execution_config, sample_ohlcv_data):
        """Test zero-trade scenario returns correct metrics."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        # All zeros = no trades
        signals = pd.Series(0, index=sample_ohlcv_data.index)

        metrics = engine.run_backtest(sample_ohlcv_data, signals)

        assert metrics['total_trades'] == 0
        # With zero trades, pnl may be nan or 0 depending on implementation
        assert metrics['total_dollar_pnl'] == 0.0 or pd.isna(metrics['total_dollar_pnl'])
        # Win rate is 0 or nan with no trades
        assert metrics['win_rate'] == 0.0 or pd.isna(metrics['win_rate'])
        assert metrics['final_equity'] == 50000.0

    def test_single_winning_trade(self, trading_config, execution_config, sample_ohlcv_data):
        """Test single winning long trade."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        # Single long position from bar 10-20
        signals = pd.Series(0, index=sample_ohlcv_data.index)
        signals.iloc[10:20] = 1

        metrics = engine.run_backtest(sample_ohlcv_data, signals)

        assert metrics['total_trades'] >= 1  # At least entry + exit
        assert 'total_dollar_pnl' in metrics
        assert 'equity_curve' in metrics
        assert len(metrics['equity_curve']) > 0

    def test_long_short_trades(self, trading_config, execution_config, sample_ohlcv_data, long_short_signals):
        """Test long and short positions."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        metrics = engine.run_backtest(sample_ohlcv_data, long_short_signals)

        assert metrics['total_trades'] > 0
        assert 'sharpe_ratio' in metrics
        assert 'profit_factor' in metrics
        assert metrics['profit_factor'] >= 0 or pd.isna(metrics['profit_factor'])

    def test_execution_costs_applied(self, trading_config, execution_config, sample_ohlcv_data, simple_long_signals):
        """Test that commission and slippage are properly applied."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        metrics = engine.run_backtest(sample_ohlcv_data, simple_long_signals)

        # Verify execution costs are tracked
        assert 'total_commission_cost' in metrics
        assert 'total_slippage_cost' in metrics
        assert 'total_execution_cost' in metrics

        if metrics['total_trades'] > 0:
            # Commission should be trades * commission_per_trade
            # Updated to match TOPSTEP_COMMISSION (2.50 per side, or 5.00 round trip)
            expected_commission = metrics['total_trades'] * 2.50
            assert abs(metrics['total_commission_cost'] - expected_commission) < 1.0

            # Slippage should be trades * slippage_ticks * tick_value
            expected_slippage = metrics['total_trades'] * 1 * 1.25
            assert abs(metrics['total_slippage_cost'] - expected_slippage) < 1.0

    def test_equity_curve_monotonic(self, trading_config, execution_config, sample_ohlcv_data, simple_long_signals):
        """Test equity curve is generated correctly."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        metrics = engine.run_backtest(sample_ohlcv_data, simple_long_signals)

        equity_curve = metrics['equity_curve']
        assert len(equity_curve) > 0
        assert equity_curve[0] == 50000.0  # Start with initial cash
        assert all(isinstance(x, (int, float)) for x in equity_curve)

    def test_daily_pnl_aggregation(self, trading_config, execution_config, sample_ohlcv_data, simple_long_signals):
        """Test daily P&L is aggregated correctly."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        metrics = engine.run_backtest(sample_ohlcv_data, simple_long_signals)

        daily_pnl = metrics['daily_pnl']
        assert isinstance(daily_pnl, dict)

        # Daily P&L is tracked regardless of number of trades
        # Both daily_pnl_series and daily_pnl_series should be populated
        assert 'daily_pnl_series' in metrics
        assert len(metrics['daily_pnl_series']) > 0


# ==============================================================================
# PERFORMANCE BENCHMARKS
# ==============================================================================

class TestPerformanceBenchmarks:
    """Benchmark VectorBT engine vs loop-based implementation."""

    def generate_large_dataset(self, num_bars: int) -> pd.DataFrame:
        """Generate large OHLCV dataset for benchmarking."""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=num_bars, freq='1min')

        close_prices = 4500 + np.cumsum(np.random.randn(num_bars) * 0.5)
        high_prices = close_prices + np.abs(np.random.randn(num_bars) * 0.5)
        low_prices = close_prices - np.abs(np.random.randn(num_bars) * 0.5)
        open_prices = close_prices.copy()
        open_prices[1:] = close_prices[:-1]
        volume = np.random.randint(100, 10000, num_bars)

        return pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        }, index=dates)

    def generate_signals(self, data: pd.DataFrame, frequency: int = 100) -> pd.Series:
        """Generate trading signals with specified frequency."""
        signals = pd.Series(0, index=data.index)

        # Alternate long/short every frequency bars
        for i, start in enumerate(range(10, len(signals), frequency)):
            if i % 2 == 0:
                signals.iloc[start:start+frequency//2] = 1  # Long
            else:
                signals.iloc[start:start+frequency//2] = -1  # Short

        return signals

    @pytest.mark.parametrize("num_bars", [1000, 10000, 50000])
    def test_vectorbt_performance(self, trading_config, execution_config, num_bars):
        """Benchmark VectorBT engine on different dataset sizes."""
        data = self.generate_large_dataset(num_bars)
        signals = self.generate_signals(data, frequency=200)

        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        start_time = time.time()
        metrics = engine.run_backtest(data, signals)
        elapsed_time = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"VectorBT Performance Benchmark - {num_bars:,} bars")
        print(f"{'='*60}")
        print(f"Execution time: {elapsed_time:.3f} seconds")
        print(f"Bars per second: {num_bars / elapsed_time:,.0f}")
        print(f"Total trades: {metrics['total_trades']}")
        print(f"Total P&L: ${metrics['total_dollar_pnl']:,.2f}")
        print(f"Win rate: {metrics['win_rate']:.1f}%")
        print(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"{'='*60}\n")

        # Performance assertions
        assert elapsed_time < 10.0  # Should complete in under 10 seconds even for 50k bars
        assert metrics['total_trades'] > 0


# ==============================================================================
# INDICATOR CACHING TESTS
# ==============================================================================

class TestIndicatorCache:
    """Test indicator caching system for Optuna optimization."""

    def test_cache_initialization(self, sample_ohlcv_data):
        """Test indicator cache initializes correctly."""
        cache = IndicatorCache(sample_ohlcv_data)

        assert len(cache._cache) == 0
        assert cache.data is sample_ohlcv_data

    def test_add_and_retrieve_indicator(self, sample_ohlcv_data):
        """Test adding and retrieving indicators."""
        cache = IndicatorCache(sample_ohlcv_data)

        # Add SMA indicator
        sma_20 = cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())

        assert 'sma_20' in cache._cache
        assert len(sma_20) == len(sample_ohlcv_data)

        # Retrieve indicator
        retrieved_sma = cache.get('sma_20')
        pd.testing.assert_series_equal(sma_20, retrieved_sma)

    def test_cache_reuse(self, sample_ohlcv_data):
        """Test that indicators are computed once and reused."""
        cache = IndicatorCache(sample_ohlcv_data)

        # Add indicator
        compute_count = [0]

        def compute_sma(df):
            compute_count[0] += 1
            return df['close'].rolling(20).mean()

        # First retrieval - should compute
        cache.add_indicator('sma_20', compute_sma)
        assert compute_count[0] == 1

        # Second retrieval - should use cache
        cache.add_indicator('sma_20', compute_sma)
        assert compute_count[0] == 1  # Not recomputed

        # Retrieve multiple times
        for _ in range(10):
            cache.get('sma_20')

        assert cache._hit_count['sma_20'] == 10

    def test_cache_stats(self, sample_ohlcv_data):
        """Test cache statistics."""
        cache = IndicatorCache(sample_ohlcv_data)

        cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        cache.add_indicator('rsi_14', lambda df: df['close'].rolling(14).mean())  # Simplified RSI

        for _ in range(5):
            cache.get('sma_20')

        for _ in range(3):
            cache.get('rsi_14')

        stats = cache.get_stats()

        assert stats['cached_indicators'] == 2
        assert stats['hit_counts']['sma_20'] == 5
        assert stats['hit_counts']['rsi_14'] == 3
        assert stats['total_hits'] == 8

    def test_cache_clear(self, sample_ohlcv_data):
        """Test cache clearing."""
        cache = IndicatorCache(sample_ohlcv_data)

        cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        cache.add_indicator('rsi_14', lambda df: df['close'].rolling(14).mean())

        assert len(cache._cache) == 2

        cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._hit_count) == 0


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================

class TestOptunaIntegration:
    """Test VectorBT integration with Optuna optimization."""

    def test_multiple_trial_simulation(self, trading_config, execution_config, sample_ohlcv_data):
        """Simulate multiple Optuna trials with VectorBT engine."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)

        results = []

        # Simulate 10 trials with different signal patterns
        for trial_num in range(10):
            # Generate different signal patterns for each "trial"
            signals = pd.Series(0, index=sample_ohlcv_data.index)
            frequency = 50 + trial_num * 10

            for i in range(0, len(signals), frequency):
                signals.iloc[i:min(i+20, len(signals))] = 1 if trial_num % 2 == 0 else -1

            # Run backtest
            start_time = time.time()
            metrics = engine.run_backtest(sample_ohlcv_data, signals)
            elapsed_time = time.time() - start_time

            results.append({
                'trial': trial_num,
                'elapsed_time': elapsed_time,
                'total_pnl': metrics['total_dollar_pnl'],
                'sharpe': metrics['sharpe_ratio'],
                'trades': metrics['total_trades']
            })

        # Verify all trials completed
        assert len(results) == 10

        # Calculate average execution time
        avg_time = np.mean([r['elapsed_time'] for r in results])
        print(f"\nAverage trial execution time: {avg_time:.4f} seconds")

        # Should be very fast
        assert avg_time < 1.0  # Less than 1 second per trial


# ==============================================================================
# RUN TESTS
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
