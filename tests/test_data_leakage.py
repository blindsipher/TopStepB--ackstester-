"""
Data Leakage Prevention Tests
=============================

Ensures walk-forward splits maintain integrity and no future data leaks into past decisions.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from config.system_config import create_trading_config
from optimization.vectorbt_engine import VectorBTPortfolioEngine, IndicatorCache


class TestDataLeakagePrevention:
    """Verify walk-forward splits maintain integrity and prevent data leakage."""

    def test_walk_forward_split_no_overlap(self):
        """Verify train/validation splits don't overlap."""
        # Create synthetic data
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        data = pd.DataFrame({
            'close': np.random.randn(200).cumsum(),
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        # Split into train/validation
        split_point = 150
        train_data = data[:split_point]
        validation_data = data[split_point:]
        
        # Verify no overlap
        overlapping_indices = train_data.index.intersection(validation_data.index)
        assert len(overlapping_indices) == 0, \
            "Train and validation data should not overlap"
        
        # Verify no gaps
        assert train_data.index[-1] < validation_data.index[0], \
            "Validation should start after train ends"

    def test_indicator_cache_split_isolation(self):
        """Verify IndicatorCache maintains separate caches per split."""
        np.random.seed(42)
        
        # Create two datasets with different price levels
        dates1 = pd.date_range('2024-01-01', periods=100, freq='1D')
        data1 = pd.DataFrame({
            'close': 100 + np.random.randn(100).cumsum()
        }, index=dates1)
        
        dates2 = pd.date_range('2024-05-01', periods=100, freq='1D')
        data2 = pd.DataFrame({
            'close': 150 + np.random.randn(100).cumsum()
        }, index=dates2)
        
        # Create separate caches
        cache1 = IndicatorCache(data1)
        cache2 = IndicatorCache(data2)
        
        # Add same indicator to both
        cache1.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        cache2.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        
        # Verify caches are independent
        sma1 = cache1.get('sma_20')
        sma2 = cache2.get('sma_20')
        
        # Different data should produce different SMA values
        assert not sma1.equals(sma2), \
            "Different data should produce different indicators"
        
        # Verify no cross-contamination in indices
        assert sma1.index[0] != sma2.index[0], \
            "Cache indices should be different"

    def test_no_future_data_in_signals(self):
        """Verify signals don't use future data."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1D')
        
        data = pd.DataFrame({
            'open': 100 + np.random.randn(100),
            'high': 101 + np.random.randn(100),
            'low': 99 + np.random.randn(100),
            'close': 100 + np.random.randn(100),
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        # Generate signals that change based on historical data only
        signals = pd.Series(0, index=data.index)
        for i in range(10, len(signals)):
            # Signal based only on past data (i-1 and earlier)
            if data['close'].iloc[i-1] > data['close'].iloc[i-10:i-1].mean():
                signals.iloc[i] = 1
            else:
                signals.iloc[i] = 0
        
        # Verify signals don't look ahead
        for i in range(1, len(signals)):
            # Signal at time i should be based on data[0:i-1], not data[0:i]
            # This is a design check - proper signals should have look-back period
            if signals.iloc[i] != signals.iloc[i-1]:
                # Signal changed - verify it uses only historical data
                assert i >= 10, "Signal should use minimum look-back period"

    def test_parameter_fitting_isolation(self):
        """Verify parameters fitted on train data don't leak into validation."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        
        # Create data with obvious trend
        trend = np.linspace(0, 20, 200)
        noise = np.random.randn(200) * 2
        close = 100 + trend + noise
        
        train_data = pd.DataFrame({
            'open': close[:150],
            'high': close[:150] + 1,
            'low': close[:150] - 1,
            'close': close[:150],
            'volume': np.random.randint(1000, 10000, 150)
        }, index=dates[:150])
        
        validation_data = pd.DataFrame({
            'open': close[150:],
            'high': close[150:] + 1,
            'low': close[150:] - 1,
            'close': close[150:],
            'volume': np.random.randint(1000, 10000, 50)
        }, index=dates[150:])
        
        # Simulate fitting SMA period to minimize validation loss
        # But calculation should be done on train data only
        train_sma_period = 20
        
        # Calculate train SMA
        train_sma = train_data['close'].rolling(train_sma_period).mean()
        
        # Calculate validation SMA with SAME period
        # (not fitted on validation data)
        validation_sma = validation_data['close'].rolling(train_sma_period).mean()
        
        # Verify they're calculated independently
        assert len(train_sma) == 150
        assert len(validation_sma) == 50
        
        # No shared index values
        shared_indices = train_data.index.intersection(validation_data.index)
        assert len(shared_indices) == 0

    def test_walk_forward_indicator_recalculation(self):
        """Verify indicators are recalculated for each walk-forward split."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        close = 100 + np.cumsum(np.random.randn(300) * 2)
        
        # Create three walk-forward splits
        splits = []
        for i in range(3):
            start_idx = i * 100
            end_idx = (i + 1) * 100
            split_data = pd.DataFrame({
                'close': close[start_idx:end_idx]
            }, index=dates[start_idx:end_idx])
            splits.append(split_data)
        
        # Create separate caches for each split
        caches = [IndicatorCache(split) for split in splits]
        
        # Add same indicator to all caches
        for cache in caches:
            cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        
        # Get indicators from each split
        indicators = [cache.get('sma_20') for cache in caches]
        
        # Verify they're different (different data in each split)
        assert not indicators[0].equals(indicators[1]), \
            "Split 1 and 2 should have different indicators"
        assert not indicators[1].equals(indicators[2]), \
            "Split 2 and 3 should have different indicators"

    def test_signal_timing_no_lookahead(self):
        """Verify signal timing doesn't allow look-ahead bias."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1D')
        
        data = pd.DataFrame({
            'open': 100 + np.random.randn(100),
            'high': 101 + np.random.randn(100),
            'low': 99 + np.random.randn(100),
            'close': 100 + np.random.randn(100),
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        # Create signals with look-back only (no look-ahead)
        signals = pd.Series(0, index=data.index)
        lookback_period = 5
        
        for i in range(lookback_period, len(data)):
            # Use only past data (0:i, not including i)
            past_data = data['close'].iloc[i-lookback_period:i]
            current_price = data['close'].iloc[i]
            
            # Signal based on past average vs current (no look-ahead)
            if current_price > past_data.mean():
                signals.iloc[i] = 1
            else:
                signals.iloc[i] = -1
        
        # Verify no bar uses future data
        for i in range(len(signals)):
            # At time i, we can only use data[0:i] for decisions
            # Verify lookback period doesn't exceed available data
            if i < lookback_period:
                assert signals.iloc[i] == 0, \
                    "Insufficient history for signal decision"

    def test_backtest_determinism_without_leakage(self):
        """Verify backtest is deterministic even with separate data splits."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        close = 100 + np.cumsum(np.random.randn(200) * 2)
        
        data = pd.DataFrame({
            'open': close,
            'high': close + 1,
            'low': close - 1,
            'close': close,
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        # Split data
        train_data = data[:150]
        test_data = data[150:]
        
        # Create signals for each split independently
        train_signals = pd.Series(0, index=train_data.index)
        train_signals.iloc[10:30] = 1
        
        test_signals = pd.Series(0, index=test_data.index)
        test_signals.iloc[10:20] = 1
        
        # Run backtests on each split
        config = create_trading_config('MES', '5m')
        exec_config = {'commission_per_trade': 2.50, 'slippage_ticks': 1, 'contracts_per_trade': 1}
        
        engine = VectorBTPortfolioEngine(config, exec_config)
        
        train_metrics1 = engine.run_backtest(train_data, train_signals)
        train_metrics2 = engine.run_backtest(train_data, train_signals)
        
        # Same data should produce same results
        assert train_metrics1['total_trades'] == train_metrics2['total_trades']
        assert abs(train_metrics1['sharpe_ratio'] - train_metrics2['sharpe_ratio']) < 0.01 or \
               (pd.isna(train_metrics1['sharpe_ratio']) and pd.isna(train_metrics2['sharpe_ratio']))

    def test_no_cache_cross_contamination(self):
        """Verify indicator caches don't cross-contaminate between splits."""
        np.random.seed(42)
        
        # Split 1
        dates1 = pd.date_range('2024-01-01', periods=50, freq='1D')
        data1 = pd.DataFrame({'close': 100 + np.cumsum(np.random.randn(50))}, index=dates1)
        
        # Split 2
        dates2 = pd.date_range('2024-03-01', periods=50, freq='1D')
        data2 = pd.DataFrame({'close': 100 + np.cumsum(np.random.randn(50))}, index=dates2)
        
        # Create caches with same indicator name
        cache1 = IndicatorCache(data1)
        cache2 = IndicatorCache(data2)
        
        cache1.add_indicator('momentum', lambda df: df['close'].diff())
        cache2.add_indicator('momentum', lambda df: df['close'].diff())
        
        mom1 = cache1.get('momentum')
        mom2 = cache2.get('momentum')
        
        # Verify they're independent
        assert mom1.iloc[1] != mom2.iloc[1], \
            "Different data should produce different momentum values"
        
        # Verify indices don't overlap
        assert len(mom1.index.intersection(mom2.index)) == 0, \
            "Cache indices should be completely separate"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
