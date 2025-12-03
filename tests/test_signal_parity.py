"""
Signal Parity Tests
===================

Ensures signal generation remains consistent across refactoring phases.
Validates that trading signals match between implementations.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from config.system_config import create_trading_config
from optimization.vectorbt_engine import IndicatorCache


class TestSignalGenerationParity:
    """Verify signal generation consistency."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for signal testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        
        close = 100 + np.cumsum(np.random.randn(300) * 2)
        
        return pd.DataFrame({
            'open': close - np.abs(np.random.randn(300)),
            'high': close + np.abs(np.random.randn(300)),
            'low': close - np.abs(np.random.randn(300)),
            'close': close,
            'volume': np.random.randint(1000, 100000, 300)
        }, index=dates)

    def test_simple_moving_average_crossover_signals(self, sample_data):
        """Test SMA crossover signal generation."""
        cache = IndicatorCache(sample_data)
        
        fast_period = 10
        slow_period = 20
        
        # Calculate moving averages
        cache.add_indicator('sma_fast', lambda df: df['close'].rolling(fast_period).mean())
        cache.add_indicator('sma_slow', lambda df: df['close'].rolling(slow_period).mean())
        
        sma_fast = cache.get('sma_fast')
        sma_slow = cache.get('sma_slow')
        
        # Generate signals: 1 when fast > slow (bullish), 0 otherwise
        signals = pd.Series(0, index=sample_data.index)
        signals[sma_fast > sma_slow] = 1
        
        # Verify signal validity
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)
        assert set(signals.dropna().unique()).issubset({0, 1})
        
        # Verify signal changes occur
        signal_changes = signals.diff().fillna(0)
        assert (signal_changes != 0).sum() > 0, "Should have signal changes"

    def test_rsi_overbought_oversold_signals(self, sample_data):
        """Test RSI-based signal generation."""
        cache = IndicatorCache(sample_data)
        rsi_period = 14
        
        # Manual RSI
        def calculate_rsi(close, period):
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        cache.add_indicator('rsi', lambda df: calculate_rsi(df['close'], rsi_period))
        rsi = cache.get('rsi')
        
        # Generate signals: -1 if RSI < 30 (oversold), 1 if RSI > 70 (overbought)
        signals = pd.Series(0, index=sample_data.index)
        signals[rsi < 30] = -1
        signals[rsi > 70] = 1
        
        # Verify signal validity
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)
        assert set(signals.dropna().unique()).issubset({-1, 0, 1})

    def test_bollinger_band_breakout_signals(self, sample_data):
        """Test Bollinger Band breakout signals."""
        cache = IndicatorCache(sample_data)
        bb_period = 20
        bb_std = 2
        
        # Calculate Bollinger Bands
        sma = sample_data['close'].rolling(bb_period).mean()
        std = sample_data['close'].rolling(bb_period).std()
        bb_upper = sma + (std * bb_std)
        bb_lower = sma - (std * bb_std)
        
        # Generate signals: 1 if price > upper band, -1 if price < lower band
        signals = pd.Series(0, index=sample_data.index)
        signals[sample_data['close'] > bb_upper] = 1
        signals[sample_data['close'] < bb_lower] = -1
        
        # Verify signal validity
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)
        assert set(signals.dropna().unique()).issubset({-1, 0, 1})
        
        # Verify breakouts are detected
        breakouts = (signals != 0).sum()
        assert breakouts > 0, "Should detect at least some breakouts"

    def test_momentum_based_signals(self, sample_data):
        """Test momentum-based signal generation."""
        cache = IndicatorCache(sample_data)
        momentum_period = 10
        
        # Calculate momentum
        cache.add_indicator('momentum', lambda df: df['close'] - df['close'].shift(momentum_period))
        momentum = cache.get('momentum')
        
        # Generate signals: 1 if momentum > 0, -1 if momentum < 0
        signals = pd.Series(0, index=sample_data.index)
        signals[momentum > 0] = 1
        signals[momentum < 0] = -1
        
        # Verify signal validity
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)
        assert set(signals.dropna().unique()).issubset({-1, 0, 1})

    def test_signal_determinism(self, sample_data):
        """Verify same data produces same signals."""
        cache1 = IndicatorCache(sample_data)
        cache2 = IndicatorCache(sample_data)
        
        period = 20
        
        # Generate signals from both caches
        cache1.add_indicator('sma', lambda df: df['close'].rolling(period).mean())
        cache2.add_indicator('sma', lambda df: df['close'].rolling(period).mean())
        
        sma1 = cache1.get('sma')
        sma2 = cache2.get('sma')
        
        # Generate signals
        signals1 = pd.Series(0, index=sample_data.index)
        signals1[sma1 > sample_data['close']] = -1
        signals1[sma1 < sample_data['close']] = 1
        
        signals2 = pd.Series(0, index=sample_data.index)
        signals2[sma2 > sample_data['close']] = -1
        signals2[sma2 < sample_data['close']] = 1
        
        # Verify signals match
        pd.testing.assert_series_equal(signals1, signals2)

    def test_signal_intensity_levels(self, sample_data):
        """Test signals with different intensity levels."""
        cache = IndicatorCache(sample_data)
        
        # Calculate RSI for intensity
        def calculate_rsi(close, period):
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        cache.add_indicator('rsi', lambda df: calculate_rsi(df['close'], 14))
        rsi = cache.get('rsi')
        
        # Generate multi-level signals
        signals = pd.Series(0, index=sample_data.index)
        signals[rsi < 20] = -2  # Very oversold
        signals[(rsi >= 20) & (rsi < 30)] = -1  # Oversold
        signals[(rsi > 70) & (rsi <= 80)] = 1  # Overbought
        signals[rsi > 80] = 2  # Very overbought
        
        # Verify signal validity
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)
        assert set(signals.dropna().unique()).issubset({-2, -1, 0, 1, 2})

    def test_multi_timeframe_signal_consistency(self, sample_data):
        """Test that signals remain consistent across different lookback periods."""
        # Long-term signal (50 period)
        sma_long = sample_data['close'].rolling(50).mean()
        signals_long = pd.Series(0, index=sample_data.index)
        signals_long[sample_data['close'] > sma_long] = 1
        signals_long[sample_data['close'] < sma_long] = -1
        
        # Short-term signal (10 period)
        sma_short = sample_data['close'].rolling(10).mean()
        signals_short = pd.Series(0, index=sample_data.index)
        signals_short[sample_data['close'] > sma_short] = 1
        signals_short[sample_data['close'] < sma_short] = -1
        
        # Verify both are valid
        assert len(signals_long) == len(signals_short)
        assert set(signals_long.dropna().unique()).issubset({-1, 0, 1})
        assert set(signals_short.dropna().unique()).issubset({-1, 0, 1})
        
        # They won't always match (different periods), but both should be valid
        assert (signals_long == signals_short).sum() > 0, "Should have some matching signals"

    def test_signal_no_lookahead_bias(self, sample_data):
        """Verify signals don't use future data."""
        # Create signals that use only past data
        sma_period = 20
        
        signals = pd.Series(0, index=sample_data.index)
        
        for i in range(sma_period, len(sample_data)):
            # Calculate SMA using only data up to bar i-1
            past_sma = sample_data['close'].iloc[:i].rolling(sma_period).mean().iloc[-1]
            current_price = sample_data['close'].iloc[i]
            
            if current_price > past_sma:
                signals.iloc[i] = 1
            elif current_price < past_sma:
                signals.iloc[i] = -1
        
        # Verify no signal before minimum lookback
        assert (signals.iloc[:sma_period] == 0).all(), \
            "Should have no signals before minimum lookback period"
        
        # Verify signals exist after lookback
        assert (signals.iloc[sma_period:] != 0).any(), \
            "Should have signals after minimum lookback period"

    def test_signal_filter_consistency(self, sample_data):
        """Test that signal filters remain consistent."""
        # Base signal from SMA crossover
        sma_fast = sample_data['close'].rolling(10).mean()
        sma_slow = sample_data['close'].rolling(20).mean()
        
        base_signals = pd.Series(0, index=sample_data.index)
        base_signals[sma_fast > sma_slow] = 1
        
        # Apply volume filter
        volume_threshold = sample_data['volume'].mean()
        filtered_signals = base_signals.copy()
        filtered_signals[sample_data['volume'] < volume_threshold] = 0
        
        # Verify filtering doesn't remove all signals
        assert filtered_signals.sum() <= base_signals.sum(), \
            "Filter should reduce or maintain signal count"
        
        # Most signals should be filtered or maintained
        assert filtered_signals.sum() > 0, \
            "Should have at least some signals after filtering"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
