"""
Unit Tests for Market Regime Detector
======================================

Comprehensive test suite for regime detection system:
1. Test on synthetic data with known regime patterns
2. Test on realistic market data
3. Validate regime transitions
4. Test edge cases and error handling
5. Validate integration with data pipeline

Author: Claude Code
Date: 2025-11-20
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import regime detector functions
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from TopStepB.data.regime_detector import (
    detect_regime,
    detect_regime_with_indicators,
    filter_by_regime,
    calculate_regime_statistics,
    add_regime_to_data,
    calculate_adx,
    calculate_volatility,
    calculate_momentum,
    calculate_range_compression,
    classify_regime
)


# ============================================================================
# Synthetic Data Generators
# ============================================================================

def create_trending_data(bars: int = 500, trend_strength: float = 0.001) -> pd.DataFrame:
    """Create synthetic data with a strong trend."""
    dates = pd.date_range('2020-01-01', periods=bars, freq='15min')

    # Create strong trending price action
    np.random.seed(42)
    trend = np.arange(bars) * trend_strength
    noise = np.random.normal(0, 0.0002, bars)
    returns = trend + noise

    base_price = 4000.0
    prices = base_price * (1 + returns).cumprod()

    # Create OHLC with tight ranges (trending market characteristic)
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = prices[i-1] if i > 0 else close
        volatility = 0.0005  # Low intrabar volatility
        high = max(open_price, close) * (1 + volatility)
        low = min(open_price, close) * (1 - volatility)

        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 1000
        })

    return pd.DataFrame(data)


def create_mean_reverting_data(bars: int = 500, range_width: float = 20.0) -> pd.DataFrame:
    """Create synthetic data with mean-reverting behavior."""
    dates = pd.date_range('2020-01-01', periods=bars, freq='15min')

    # Create oscillating price action around a mean
    np.random.seed(43)
    base_price = 4000.0
    oscillation = np.sin(np.arange(bars) * 0.1) * range_width
    noise = np.random.normal(0, 5, bars)
    prices = base_price + oscillation + noise

    # Create OHLC with wider ranges (mean-reverting characteristic)
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = prices[i-1] if i > 0 else close
        volatility = 0.003  # Higher intrabar volatility
        high = max(open_price, close) * (1 + volatility)
        low = min(open_price, close) * (1 - volatility)

        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 1000
        })

    return pd.DataFrame(data)


def create_choppy_data(bars: int = 500) -> pd.DataFrame:
    """Create synthetic data with choppy, directionless behavior."""
    dates = pd.date_range('2020-01-01', periods=bars, freq='15min')

    # Create random walk with very small steps
    np.random.seed(44)
    base_price = 4000.0
    returns = np.random.normal(0, 0.0001, bars)  # Very low volatility
    prices = base_price * (1 + returns).cumprod()

    # Create OHLC with very tight ranges (choppy characteristic)
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = prices[i-1] if i > 0 else close
        volatility = 0.0002  # Very low intrabar volatility
        high = max(open_price, close) * (1 + volatility)
        low = min(open_price, close) * (1 - volatility)

        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 1000
        })

    return pd.DataFrame(data)


def create_mixed_regime_data(bars: int = 1500) -> pd.DataFrame:
    """Create data with different regimes in sequence."""
    # Combine trending, mean-reverting, and choppy data
    trending = create_trending_data(bars // 3)
    mean_reverting = create_mean_reverting_data(bars // 3)
    choppy = create_choppy_data(bars // 3)

    # Adjust timestamps to be sequential
    trending['datetime'] = pd.date_range('2020-01-01', periods=len(trending), freq='15min')
    mean_reverting['datetime'] = pd.date_range(
        trending['datetime'].iloc[-1] + timedelta(minutes=15),
        periods=len(mean_reverting),
        freq='15min'
    )
    choppy['datetime'] = pd.date_range(
        mean_reverting['datetime'].iloc[-1] + timedelta(minutes=15),
        periods=len(choppy),
        freq='15min'
    )

    # Normalize prices to connect smoothly
    mean_reverting_base = trending['close'].iloc[-1]
    mean_reverting['open'] += (mean_reverting_base - mean_reverting['open'].iloc[0])
    mean_reverting['high'] += (mean_reverting_base - mean_reverting['close'].iloc[0])
    mean_reverting['low'] += (mean_reverting_base - mean_reverting['close'].iloc[0])
    mean_reverting['close'] += (mean_reverting_base - mean_reverting['close'].iloc[0])

    choppy_base = mean_reverting['close'].iloc[-1]
    choppy['open'] += (choppy_base - choppy['open'].iloc[0])
    choppy['high'] += (choppy_base - choppy['close'].iloc[0])
    choppy['low'] += (choppy_base - choppy['close'].iloc[0])
    choppy['close'] += (choppy_base - choppy['close'].iloc[0])

    return pd.concat([trending, mean_reverting, choppy], ignore_index=True)


# ============================================================================
# Tests - Basic Functionality
# ============================================================================

def test_detect_regime_basic():
    """Test basic regime detection on synthetic data."""
    data = create_trending_data(bars=500)
    regimes = detect_regime(data, lookback=100)

    assert len(regimes) == len(data)
    assert regimes.name == 'regime'
    assert set(regimes.unique()).issubset({'trending', 'mean_reverting', 'choppy', 'unknown'})


def test_detect_regime_insufficient_data():
    """Test that insufficient data raises ValueError."""
    data = create_trending_data(bars=50)

    with pytest.raises(ValueError, match="Insufficient data"):
        detect_regime(data, lookback=100)


def test_detect_regime_missing_columns():
    """Test that missing columns raises ValueError."""
    data = pd.DataFrame({
        'datetime': pd.date_range('2020-01-01', periods=100, freq='15min'),
        'close': np.random.randn(100)
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        detect_regime(data, lookback=50)


def test_detect_regime_trending_data():
    """Test that trending data is correctly identified."""
    data = create_trending_data(bars=500, trend_strength=0.002)
    regimes = detect_regime(data, lookback=100)

    # After lookback period, should see significant trending
    post_lookback_regimes = regimes[100:]
    trending_pct = (post_lookback_regimes == 'trending').sum() / len(post_lookback_regimes)

    print(f"Trending data regime distribution: {post_lookback_regimes.value_counts().to_dict()}")
    assert trending_pct > 0.3, f"Expected >30% trending, got {trending_pct*100:.1f}%"


def test_detect_regime_mean_reverting_data():
    """Test that mean-reverting data is correctly identified."""
    data = create_mean_reverting_data(bars=500, range_width=30.0)
    regimes = detect_regime(data, lookback=100)

    post_lookback_regimes = regimes[100:]
    mean_reverting_pct = (post_lookback_regimes == 'mean_reverting').sum() / len(post_lookback_regimes)

    print(f"Mean-reverting data regime distribution: {post_lookback_regimes.value_counts().to_dict()}")
    assert mean_reverting_pct > 0.2, f"Expected >20% mean-reverting, got {mean_reverting_pct*100:.1f}%"


def test_detect_regime_choppy_data():
    """Test that choppy data is correctly identified."""
    data = create_choppy_data(bars=500)
    regimes = detect_regime(data, lookback=100)

    post_lookback_regimes = regimes[100:]
    choppy_pct = (post_lookback_regimes == 'choppy').sum() / len(post_lookback_regimes)

    print(f"Choppy data regime distribution: {post_lookback_regimes.value_counts().to_dict()}")
    assert choppy_pct > 0.4, f"Expected >40% choppy, got {choppy_pct*100:.1f}%"


# ============================================================================
# Tests - Indicator Calculations
# ============================================================================

def test_calculate_adx():
    """Test ADX calculation."""
    data = create_trending_data(bars=200)
    adx = calculate_adx(data['high'], data['low'], data['close'], period=14)

    assert len(adx) == len(data)
    assert not adx.isna().all()
    assert (adx >= 0).all()  # ADX should be non-negative


def test_calculate_volatility():
    """Test volatility calculation."""
    data = create_mean_reverting_data(bars=200)
    volatility = calculate_volatility(data['close'], period=20)

    assert len(volatility) == len(data)
    assert (volatility >= 0).all()  # Volatility should be non-negative


def test_calculate_momentum():
    """Test momentum calculation."""
    data = create_trending_data(bars=200)
    momentum = calculate_momentum(data['close'], period=20)

    assert len(momentum) == len(data)
    # Trending data should have positive momentum on average
    assert momentum[50:].mean() > 0


def test_calculate_range_compression():
    """Test range compression calculation."""
    data = create_choppy_data(bars=200)
    compression = calculate_range_compression(data['high'], data['low'], data['close'])

    assert len(compression) == len(data)
    assert (compression > 0).all()  # Compression should be positive


# ============================================================================
# Tests - Advanced Functionality
# ============================================================================

def test_detect_regime_with_indicators():
    """Test regime detection with full indicator output."""
    data = create_trending_data(bars=500)
    result = detect_regime_with_indicators(data, lookback=100)

    assert 'regime' in result.columns
    assert 'adx' in result.columns
    assert 'volatility' in result.columns
    assert 'momentum' in result.columns
    assert 'range_compression' in result.columns
    assert len(result) == len(data)


def test_filter_by_regime():
    """Test filtering data by regime."""
    data = create_mixed_regime_data(bars=1500)
    trending_data = filter_by_regime(data, 'trending', lookback=100)

    assert len(trending_data) <= len(data)
    assert all(col in trending_data.columns for col in ['open', 'high', 'low', 'close'])


def test_calculate_regime_statistics():
    """Test regime statistics calculation."""
    data = create_mixed_regime_data(bars=1500)
    regimes = detect_regime(data, lookback=100)
    stats = calculate_regime_statistics(data, regimes)

    assert 'trending' in stats
    assert 'mean_reverting' in stats
    assert 'choppy' in stats

    for regime, metrics in stats.items():
        assert 'count' in metrics
        assert 'percentage' in metrics
        assert 'mean_return' in metrics
        assert 'volatility' in metrics


def test_add_regime_to_data():
    """Test adding regime column to data."""
    data = create_trending_data(bars=500)
    data_with_regime = add_regime_to_data(data, lookback=100)

    assert 'regime' in data_with_regime.columns
    assert len(data_with_regime) == len(data)
    assert all(col in data_with_regime.columns for col in ['open', 'high', 'low', 'close', 'regime'])


# ============================================================================
# Tests - Regime Transitions
# ============================================================================

def test_regime_transitions():
    """Test that regime transitions are sensible."""
    data = create_mixed_regime_data(bars=1500)
    regimes = detect_regime(data, lookback=100)

    # Count transitions
    transitions = (regimes != regimes.shift()).sum()
    transition_rate = transitions / len(regimes)

    # Should have some transitions but not excessive (not every bar)
    assert transition_rate > 0.01, "Expected some regime transitions"
    assert transition_rate < 0.5, "Too many regime transitions (possibly unstable)"

    print(f"Transition rate: {transition_rate*100:.2f}%")


def test_regime_persistence():
    """Test that regimes persist for reasonable periods."""
    data = create_trending_data(bars=1000, trend_strength=0.002)
    regimes = detect_regime(data, lookback=100)

    # Calculate average regime duration
    regime_changes = regimes != regimes.shift()
    regime_ids = regime_changes.cumsum()
    regime_durations = regimes.groupby(regime_ids).size()

    avg_duration = regime_durations.mean()
    print(f"Average regime duration: {avg_duration:.1f} bars")

    # Regimes should persist for at least 10 bars on average
    assert avg_duration >= 10, f"Regimes change too frequently: {avg_duration:.1f} bars"


# ============================================================================
# Tests - Custom Thresholds
# ============================================================================

def test_custom_thresholds():
    """Test regime detection with custom thresholds."""
    data = create_trending_data(bars=500)

    # Strict thresholds (harder to classify as trending)
    strict_thresholds = {
        'adx_high': 35.0,
        'adx_low': 25.0,
        'volatility_high': 3.0,
        'volatility_low': 1.5,
        'momentum_threshold': 5.0,
        'compression_high': 1.3,
        'compression_low': 0.7
    }

    regimes_strict = detect_regime(data, lookback=100, thresholds=strict_thresholds)

    # Lenient thresholds (easier to classify as trending)
    lenient_thresholds = {
        'adx_high': 15.0,
        'adx_low': 10.0,
        'volatility_high': 1.5,
        'volatility_low': 0.5,
        'momentum_threshold': 1.0,
        'compression_high': 1.1,
        'compression_low': 0.9
    }

    regimes_lenient = detect_regime(data, lookback=100, thresholds=lenient_thresholds)

    # Lenient should classify more as trending
    trending_strict = (regimes_strict == 'trending').sum()
    trending_lenient = (regimes_lenient == 'trending').sum()

    print(f"Trending bars - Strict: {trending_strict}, Lenient: {trending_lenient}")
    assert trending_lenient >= trending_strict


# ============================================================================
# Tests - Edge Cases
# ============================================================================

def test_regime_with_gaps():
    """Test regime detection with data gaps."""
    data = create_trending_data(bars=500)

    # Remove some data to create gaps
    mask = np.random.random(len(data)) > 0.1  # Keep 90% of data
    data_with_gaps = data[mask].reset_index(drop=True)

    regimes = detect_regime(data_with_gaps, lookback=100)

    assert len(regimes) == len(data_with_gaps)
    assert regimes.notna().all()


def test_regime_with_extreme_values():
    """Test regime detection with extreme price movements."""
    data = create_trending_data(bars=500)

    # Add a flash crash
    data.loc[250, 'low'] = data.loc[250, 'close'] * 0.5
    data.loc[250, 'close'] = data.loc[250, 'close'] * 0.95

    # Should still work without errors
    regimes = detect_regime(data, lookback=100)

    assert len(regimes) == len(data)
    assert regimes.notna().all()


def test_regime_with_constant_prices():
    """Test regime detection with constant prices (no movement)."""
    dates = pd.date_range('2020-01-01', periods=500, freq='15min')
    data = pd.DataFrame({
        'datetime': dates,
        'open': 4000.0,
        'high': 4000.0,
        'low': 4000.0,
        'close': 4000.0,
        'volume': 1000
    })

    regimes = detect_regime(data, lookback=100)

    assert len(regimes) == len(data)
    # With no movement, should classify as choppy
    post_lookback = regimes[100:]
    assert (post_lookback == 'choppy').sum() > len(post_lookback) * 0.9


# ============================================================================
# Tests - Integration with Real Data
# ============================================================================

def test_regime_with_real_data_pattern():
    """Test regime detection with realistic ES futures pattern."""
    # Create data that mimics real ES futures behavior
    np.random.seed(100)
    bars = 2000

    # Simulate multiple market phases
    dates = pd.date_range('2020-01-01', periods=bars, freq='15min')
    base_price = 4000.0

    # Create realistic price action with regime changes
    prices = [base_price]
    for i in range(1, bars):
        # Different regimes in different periods
        if i < 500:  # Trending up
            drift = 0.0003
            vol = 0.0005
        elif i < 1000:  # Mean-reverting
            drift = -0.0001 * (prices[-1] - 4050) / 50  # Pull to 4050
            vol = 0.001
        elif i < 1500:  # Choppy
            drift = 0
            vol = 0.0002
        else:  # Trending down
            drift = -0.0003
            vol = 0.0005

        ret = np.random.normal(drift, vol)
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)

    # Create OHLC
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = prices[i-1] if i > 0 else close
        vol = abs(close - open_price) * 2
        high = max(open_price, close) + vol
        low = min(open_price, close) - vol

        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 1000
        })

    data = pd.DataFrame(data)

    # Detect regimes
    regimes = detect_regime(data, lookback=100)

    # Should have detected multiple regime types
    unique_regimes = regimes[100:].unique()
    assert len(unique_regimes) >= 2, "Should detect multiple regime types in realistic data"

    # Calculate statistics
    stats = calculate_regime_statistics(data, regimes)
    print("\nRegime statistics for realistic data:")
    for regime, metrics in stats.items():
        print(f"{regime}: {metrics['percentage']:.1f}% of data")


# ============================================================================
# Performance Tests
# ============================================================================

def test_regime_detection_performance():
    """Test that regime detection is reasonably fast."""
    import time

    data = create_trending_data(bars=5000)

    start_time = time.time()
    regimes = detect_regime(data, lookback=100)
    elapsed = time.time() - start_time

    print(f"\nRegime detection for 5000 bars took {elapsed:.3f} seconds")

    # Should complete in reasonable time (< 2 seconds for 5000 bars)
    assert elapsed < 2.0, f"Regime detection too slow: {elapsed:.3f}s"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
