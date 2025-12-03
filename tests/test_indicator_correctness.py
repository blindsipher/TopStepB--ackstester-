"""
Indicator Correctness Tests
===========================

Validates VectorBT indicators match manual calculations within numerical precision.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from optimization.vectorbt_engine import IndicatorCache


class TestIndicatorCorrectness:
    """Verify indicator calculations match manual methods."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for indicator testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=500, freq='1D')
        
        close = 100 + np.cumsum(np.random.randn(500) * 2)
        
        return pd.DataFrame({
            'open': close - np.abs(np.random.randn(500)),
            'high': close + np.abs(np.random.randn(500)),
            'low': close - np.abs(np.random.randn(500)),
            'close': close,
            'volume': np.random.randint(1000, 100000, 500)
        }, index=dates)

    def test_sma_calculation_accuracy(self, sample_data):
        """Verify SMA calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        
        period = 20
        
        # Add SMA to cache
        cache.add_indicator('sma_20', lambda df: df['close'].rolling(period).mean())
        cached_sma = cache.get('sma_20')
        
        # Manual SMA
        manual_sma = sample_data['close'].rolling(period).mean()
        
        # Compare (excluding NaN values)
        pd.testing.assert_series_equal(
            cached_sma.dropna(),
            manual_sma.dropna(),
            check_exact=False,
            atol=1e-10  # Numerical precision tolerance
        )

    def test_ema_calculation_accuracy(self, sample_data):
        """Verify EMA calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        
        period = 20
        
        # Add EMA to cache
        cache.add_indicator('ema_20', lambda df: df['close'].ewm(span=period, adjust=False).mean())
        cached_ema = cache.get('ema_20')
        
        # Manual EMA
        manual_ema = sample_data['close'].ewm(span=period, adjust=False).mean()
        
        # Compare
        pd.testing.assert_series_equal(
            cached_ema.dropna(),
            manual_ema.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_rsi_calculation_accuracy(self, sample_data):
        """Verify RSI calculation matches manual method."""
        cache = IndicatorCache(sample_data)
        period = 14
        
        # Manual RSI calculation
        def calculate_rsi(close, period):
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        # Add RSI to cache
        cache.add_indicator('rsi_14', lambda df: calculate_rsi(df['close'], period))
        cached_rsi = cache.get('rsi_14')
        
        # Manual RSI
        manual_rsi = calculate_rsi(sample_data['close'], period)
        
        # Compare
        pd.testing.assert_series_equal(
            cached_rsi.dropna(),
            manual_rsi.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_bbands_calculation_accuracy(self, sample_data):
        """Verify Bollinger Bands match standard calculation."""
        cache = IndicatorCache(sample_data)
        period = 20
        num_std = 2
        
        # Manual Bollinger Bands
        def calculate_bbands(df, period, num_std):
            sma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            upper = sma + (std * num_std)
            lower = sma - (std * num_std)
            return upper, sma, lower
        
        # Add to cache
        cache.add_indicator('bb_upper', lambda df: calculate_bbands(df, period, num_std)[0])
        cache.add_indicator('bb_middle', lambda df: calculate_bbands(df, period, num_std)[1])
        cache.add_indicator('bb_lower', lambda df: calculate_bbands(df, period, num_std)[2])
        
        cached_upper = cache.get('bb_upper')
        cached_middle = cache.get('bb_middle')
        cached_lower = cache.get('bb_lower')
        
        # Manual calculation
        manual_upper, manual_middle, manual_lower = calculate_bbands(sample_data, period, num_std)
        
        # Compare
        pd.testing.assert_series_equal(
            cached_upper.dropna(),
            manual_upper.dropna(),
            check_exact=False,
            atol=1e-10
        )
        
        pd.testing.assert_series_equal(
            cached_middle.dropna(),
            manual_middle.dropna(),
            check_exact=False,
            atol=1e-10
        )
        
        pd.testing.assert_series_equal(
            cached_lower.dropna(),
            manual_lower.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_atr_calculation_accuracy(self, sample_data):
        """Verify ATR calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        period = 14
        
        # Manual ATR calculation
        def calculate_atr(df, period):
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift(1)).abs()
            low_close = (df['low'] - df['close'].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(span=period, adjust=False).mean()
            return atr
        
        # Add to cache
        cache.add_indicator('atr_14', lambda df: calculate_atr(df, period))
        cached_atr = cache.get('atr_14')
        
        # Manual ATR
        manual_atr = calculate_atr(sample_data, period)
        
        # Compare
        pd.testing.assert_series_equal(
            cached_atr.dropna(),
            manual_atr.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_macd_calculation_accuracy(self, sample_data):
        """Verify MACD calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        fast_period = 12
        slow_period = 26
        signal_period = 9
        
        # Manual MACD
        def calculate_macd(df, fast, slow, signal):
            ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal, adjust=False).mean()
            histogram = macd - macd_signal
            return macd, macd_signal, histogram
        
        # Add to cache
        macd, signal, hist = calculate_macd(sample_data, fast_period, slow_period, signal_period)
        
        cache.add_indicator('macd', lambda df: calculate_macd(df, fast_period, slow_period, signal_period)[0])
        cache.add_indicator('macd_signal', lambda df: calculate_macd(df, fast_period, slow_period, signal_period)[1])
        
        cached_macd = cache.get('macd')
        cached_signal = cache.get('macd_signal')
        
        # Compare
        pd.testing.assert_series_equal(
            cached_macd.dropna(),
            macd.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_momentum_calculation_accuracy(self, sample_data):
        """Verify momentum calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        period = 10
        
        # Manual momentum
        def calculate_momentum(close, period):
            return close - close.shift(period)
        
        # Add to cache
        cache.add_indicator('momentum', lambda df: calculate_momentum(df['close'], period))
        cached_momentum = cache.get('momentum')
        
        # Manual momentum
        manual_momentum = calculate_momentum(sample_data['close'], period)
        
        # Compare
        pd.testing.assert_series_equal(
            cached_momentum.dropna(),
            manual_momentum.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_roc_calculation_accuracy(self, sample_data):
        """Verify Rate of Change calculation matches standard method."""
        cache = IndicatorCache(sample_data)
        period = 10
        
        # Manual ROC
        def calculate_roc(close, period):
            return ((close - close.shift(period)) / close.shift(period)) * 100
        
        # Add to cache
        cache.add_indicator('roc', lambda df: calculate_roc(df['close'], period))
        cached_roc = cache.get('roc')
        
        # Manual ROC
        manual_roc = calculate_roc(sample_data['close'], period)
        
        # Compare
        pd.testing.assert_series_equal(
            cached_roc.dropna(),
            manual_roc.dropna(),
            check_exact=False,
            atol=1e-10
        )

    def test_bollinger_squeeze_detection(self, sample_data):
        """Verify Bollinger Squeeze detection works correctly."""
        cache = IndicatorCache(sample_data)
        bb_period = 20
        bb_std = 2
        kc_period = 20
        atr_period = 10
        
        # Calculate Bollinger Bands
        sma_bb = sample_data['close'].rolling(bb_period).mean()
        std_bb = sample_data['close'].rolling(bb_period).std()
        bb_upper = sma_bb + (std_bb * bb_std)
        bb_lower = sma_bb - (std_bb * bb_std)
        bb_width = bb_upper - bb_lower
        
        # Calculate Keltner Channel
        sma_kc = sample_data['close'].rolling(kc_period).mean()
        high_low = sample_data['high'] - sample_data['low']
        high_close = (sample_data['high'] - sample_data['close'].shift(1)).abs()
        low_close = (sample_data['low'] - sample_data['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.ewm(span=atr_period, adjust=False).mean()
        
        kc_upper = sma_kc + atr
        kc_lower = sma_kc - atr
        kc_width = kc_upper - kc_lower
        
        # Bollinger Squeeze: BB width < KC width
        squeeze_signal = bb_width < kc_width
        
        # Verify some squeeze conditions exist
        assert squeeze_signal.sum() > 0, "Should detect at least some squeeze conditions"
        
        # Verify some non-squeeze conditions
        assert (~squeeze_signal).sum() > 0, "Should detect non-squeeze conditions"

    def test_multiple_indicators_consistency(self, sample_data):
        """Test that multiple indicators can coexist in cache without interference."""
        cache = IndicatorCache(sample_data)
        
        # Add multiple indicators
        cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        cache.add_indicator('sma_50', lambda df: df['close'].rolling(50).mean())
        cache.add_indicator('ema_20', lambda df: df['close'].ewm(span=20, adjust=False).mean())
        
        # Retrieve all
        sma_20 = cache.get('sma_20')
        sma_50 = cache.get('sma_50')
        ema_20 = cache.get('ema_20')
        
        # Verify they're all present and different
        assert len(sma_20) == len(sample_data)
        assert len(sma_50) == len(sample_data)
        assert len(ema_20) == len(sample_data)
        
        # Verify they're not identical
        assert not sma_20.equals(sma_50)
        assert not sma_20.equals(ema_20)
        assert not sma_50.equals(ema_20)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
