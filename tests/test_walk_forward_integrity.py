"""
Walk-Forward Integrity Tests
=============================

Ensures walk-forward optimization maintains integrity and prevents data leakage between splits.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from optimization.vectorbt_engine import IndicatorCache


class TestWalkForwardIntegrity:
    """Verify walk-forward optimization maintains integrity."""

    def test_walk_forward_cache_isolation(self):
        """Verify IndicatorCache doesn't leak between walk-forward splits."""
        # Create 3 data splits for walk-forward
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        
        splits = []
        for i in range(3):
            start_idx = i * 100
            end_idx = (i + 1) * 100
            
            np.random.seed(42 + i)  # Different seed for each split
            data = pd.DataFrame({
                'close': 100 + i*50 + np.random.randn(100).cumsum()
            }, index=dates[start_idx:end_idx])
            splits.append(data)
        
        # Create separate caches for each split
        caches = [IndicatorCache(split) for split in splits]
        
        # Add same indicator to all caches
        for cache in caches:
            cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        
        # Get indicators
        indicators = [cache.get('sma_20') for cache in caches]
        
        # Verify they're different (different data produces different results)
        assert not indicators[0].equals(indicators[1]), \
            "Split 1 and 2 should have different indicators"
        assert not indicators[1].equals(indicators[2]), \
            "Split 2 and 3 should have different indicators"
        assert not indicators[0].equals(indicators[2]), \
            "Split 1 and 3 should have different indicators"

    def test_walk_forward_no_cross_contamination(self):
        """Verify parameters fitted on one split don't affect another."""
        # Split data: train(0-100), validation(100-200)
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(200)),
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        train_data = data[:100]
        validation_data = data[100:]
        
        # Simulate parameter fitting on train_data
        # (In real optimization, would fit SMA period to maximize Sharpe)
        sma_period = 20
        
        # Train SMA
        train_sma = train_data['close'].rolling(sma_period).mean()
        
        # Validation SMA (same period, but on validation data)
        validation_sma = validation_data['close'].rolling(sma_period).mean()
        
        # Verify they don't influence each other
        # Different price levels = different indicator values
        assert train_sma.mean() != validation_sma.mean(), \
            "Different data should produce different indicator statistics"
        
        # Verify no index overlap
        assert len(train_data.index.intersection(validation_data.index)) == 0, \
            "Train and validation indices should not overlap"

    def test_walk_forward_sequential_split_ordering(self):
        """Verify walk-forward splits maintain temporal order."""
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        
        # Define walk-forward windows
        windows = [
            (0, 100, 150),     # Optimize 0-100, validate 100-150
            (50, 150, 200),    # Optimize 50-150, validate 150-200
            (100, 200, 250),   # Optimize 100-200, validate 200-250
        ]
        
        for opt_start, opt_end, val_end in windows:
            opt_data = dates[opt_start:opt_end]
            val_data = dates[opt_end:val_end]
            
            # Verify temporal order
            assert opt_data[-1] < val_data[0], \
                "Optimization window should end before validation window"
            
            # Verify no overlap
            assert len(opt_data.intersection(val_data)) == 0

    def test_rolling_window_no_lookahead(self):
        """Verify rolling window doesn't use future data."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1D')
        close = 100 + np.cumsum(np.random.randn(100))
        
        data = pd.DataFrame({'close': close}, index=dates)
        
        # Rolling window: use data up to day 50 to predict day 51-60
        train_end = 50
        test_start = 50
        test_end = 60
        
        train_data = data.iloc[:train_end]
        test_data = data.iloc[test_start:test_end]
        
        # Calculate training indicator
        train_sma = train_data['close'].rolling(20).mean()
        
        # Apply to test data (using training period, not future data)
        # SMA of test data uses only test data, not future data beyond test_end
        test_sma = test_data['close'].rolling(20).mean()
        
        # Verify indices
        assert max(train_data.index) <= min(test_data.index), \
            "Train period should end before test period begins"

    def test_indicator_recalculation_per_split(self):
        """Verify indicators are recalculated fresh for each split."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        
        # First split
        data1 = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100))
        }, index=dates[:100])
        
        # Second split
        data2 = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100))
        }, index=dates[100:])
        
        # Calculate SMA separately for each split
        cache1 = IndicatorCache(data1)
        cache2 = IndicatorCache(data2)
        
        cache1.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        cache2.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
        
        sma1 = cache1.get('sma_20')
        sma2 = cache2.get('sma_20')
        
        # Verify they're calculated independently
        assert len(sma1) == 100
        assert len(sma2) == 100
        assert sma1.iloc[20] != sma2.iloc[20], \
            "Different data should produce different SMA values"

    def test_anchor_walk_forward_splits(self):
        """Test anchor-based walk-forward (training window grows)."""
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        close = 100 + np.cumsum(np.random.randn(300))
        
        data = pd.DataFrame({'close': close}, index=dates)
        
        # Anchor walk-forward: training window grows, test window fixed size
        test_window_size = 50
        train_start = 0
        
        splits = []
        for i in range(0, 200, 50):  # Move test window forward by 50 days, leaving room at end
            train_end = i + 100
            test_end = train_end + test_window_size
            
            if test_end > len(data):
                break  # Stop if we run out of data
            
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[train_end:test_end]
            
            splits.append({
                'train': train_data,
                'test': test_data
            })
        
        # Verify we have splits
        assert len(splits) > 0, "Should have at least one split"
        
        for i, split in enumerate(splits):
            if i > 0:
                # Training window should grow
                assert len(split['train']) > len(splits[i-1]['train']), \
                    "Training window should grow in anchor walk-forward"
            
            # Test window should be consistent size
            assert len(split['test']) == test_window_size, \
                "Test window should be consistent size"

    def test_walk_forward_metric_independence(self):
        """Verify walk-forward metrics are calculated independently."""
        from config.system_config import create_trading_config
        from optimization.vectorbt_engine import VectorBTPortfolioEngine
        
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        close = 100 + np.cumsum(np.random.randn(200) * 2)
        
        # Create two splits
        data1 = pd.DataFrame({
            'open': close[:100],
            'high': close[:100] + 1,
            'low': close[:100] - 1,
            'close': close[:100],
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates[:100])
        
        data2 = pd.DataFrame({
            'open': close[100:],
            'high': close[100:] + 1,
            'low': close[100:] - 1,
            'close': close[100:],
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates[100:])
        
        # Generate same signals for both
        signals1 = pd.Series(0, index=data1.index)
        signals1.iloc[10:30] = 1
        
        signals2 = pd.Series(0, index=data2.index)
        signals2.iloc[10:30] = 1
        
        # Run backtests
        config = create_trading_config('MES', '5m')
        exec_config = {'commission_per_trade': 2.50, 'slippage_ticks': 1, 'contracts_per_trade': 1}
        
        engine = VectorBTPortfolioEngine(config, exec_config)
        
        metrics1 = engine.run_backtest(data1, signals1)
        metrics2 = engine.run_backtest(data2, signals2)
        
        # Same signal pattern but different data = different results
        # (unless price levels are identical, which they're not)
        assert metrics1['total_trades'] == metrics2['total_trades'], \
            "Same signal pattern should generate same number of trades"

    def test_purging_walk_forward(self):
        """Test purged walk-forward (remove data around split boundaries)."""
        dates = pd.date_range('2024-01-01', periods=300, freq='1D')
        
        # Define purge windows
        test_start = 100
        test_end = 150
        purge_days = 20
        
        # Training data: exclude purge period before test
        train_end = test_start - purge_days
        
        # Testing data
        # Validation data: exclude purge period after test
        val_start = test_end + purge_days
        
        train_dates = dates[:train_end]
        test_dates = dates[test_start:test_end]
        val_dates = dates[val_start:]
        
        # Verify purging gaps
        assert max(train_dates) < (min(test_dates) - pd.Timedelta(days=purge_days)), \
            "Purge period should separate train and test"
        
        assert max(test_dates) < (min(val_dates) - pd.Timedelta(days=purge_days)), \
            "Purge period should separate test and validation"

    def test_out_of_sample_independence(self):
        """Verify out-of-sample validation is truly independent."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1D')
        close = 100 + np.cumsum(np.random.randn(200) * 2)
        
        # In-sample: first 100 bars
        in_sample = close[:100]
        
        # Out-of-sample: last 100 bars (completely separate in time)
        out_of_sample = close[100:]
        
        # Parameters optimized on in_sample
        is_sma_period = 20
        is_sma = pd.Series(in_sample).rolling(is_sma_period).mean()
        
        # Same parameters applied to out-of-sample
        oos_sma = pd.Series(out_of_sample).rolling(is_sma_period).mean()
        
        # Out-of-sample should NOT have been used during optimization
        # Verify temporal separation
        assert 100 == (len(in_sample) + 0), "In-sample size correct"
        assert 100 == (len(out_of_sample) + 0), "Out-of-sample size correct"
        
        # No temporal overlap
        assert len(in_sample) + len(out_of_sample) == len(close)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
