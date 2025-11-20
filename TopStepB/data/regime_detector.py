"""
Market Regime Detection System
===============================

Robust regime classifier for futures trading that detects:
1. Trending markets (high ADX, directional movement)
2. Mean-reverting markets (low ADX, high volatility, range-bound)
3. Choppy/sideways markets (low ADX, low volatility)

Key Features:
- Real-time regime classification from OHLCV data
- Configurable lookback periods
- Multiple regime indicators (ADX, volatility, trend strength)
- Fast computation (Numba-compiled where beneficial)
- Integration with existing data pipeline

Author: Claude Code
Date: 2025-11-20
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from numba import jit

logger = logging.getLogger(__name__)


# ============================================================================
# Core Technical Indicators (Numba-optimized)
# ============================================================================

@jit(nopython=True)
def calculate_true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """
    Calculate True Range for ATR calculation.

    TR = max(high - low, abs(high - prev_close), abs(low - prev_close))

    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of close prices

    Returns:
        Array of true range values
    """
    n = len(high)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]  # First bar has no previous close

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    return tr


@jit(nopython=True)
def calculate_atr(true_range: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Average True Range using Wilder's smoothing.

    Args:
        true_range: Array of true range values
        period: Lookback period for ATR

    Returns:
        Array of ATR values
    """
    n = len(true_range)
    atr = np.zeros(n)

    # First ATR is simple average
    if n >= period:
        atr[period-1] = np.mean(true_range[:period])

        # Subsequent ATR uses Wilder's smoothing
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period - 1) + true_range[i]) / period

    return atr


@jit(nopython=True)
def calculate_directional_movement(high: np.ndarray, low: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate +DM and -DM for ADX calculation.

    Args:
        high: Array of high prices
        low: Array of low prices

    Returns:
        Tuple of (+DM, -DM) arrays
    """
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        up_move = high[i] - high[i-1]
        down_move = low[i-1] - low[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move

        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

    return plus_dm, minus_dm


@jit(nopython=True)
def smooth_directional_indicators(values: np.ndarray, period: int) -> np.ndarray:
    """
    Smooth directional indicators using Wilder's smoothing.

    Args:
        values: Array of values to smooth
        period: Smoothing period

    Returns:
        Array of smoothed values
    """
    n = len(values)
    smoothed = np.zeros(n)

    if n >= period:
        # First value is simple sum
        smoothed[period-1] = np.sum(values[:period])

        # Subsequent values use Wilder's smoothing
        for i in range(period, n):
            smoothed[i] = smoothed[i-1] - (smoothed[i-1] / period) + values[i]

    return smoothed


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average Directional Index (ADX).

    ADX measures trend strength regardless of direction:
    - Values above 25: Strong trend
    - Values 20-25: Moderate trend
    - Values below 20: Weak trend or ranging

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default 14)

    Returns:
        Series of ADX values
    """
    high_np = high.values
    low_np = low.values
    close_np = close.values

    # Calculate True Range and ATR
    tr = calculate_true_range(high_np, low_np, close_np)
    atr = calculate_atr(tr, period)

    # Calculate Directional Movement
    plus_dm, minus_dm = calculate_directional_movement(high_np, low_np)

    # Smooth DM values
    plus_dm_smooth = smooth_directional_indicators(plus_dm, period)
    minus_dm_smooth = smooth_directional_indicators(minus_dm, period)

    # Calculate Directional Indicators
    plus_di = np.zeros(len(high))
    minus_di = np.zeros(len(high))

    for i in range(len(high)):
        if atr[i] != 0:
            plus_di[i] = 100 * plus_dm_smooth[i] / atr[i]
            minus_di[i] = 100 * minus_dm_smooth[i] / atr[i]

    # Calculate DX
    dx = np.zeros(len(high))
    for i in range(len(high)):
        di_sum = plus_di[i] + minus_di[i]
        if di_sum != 0:
            dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / di_sum

    # Calculate ADX (smoothed DX)
    adx = smooth_directional_indicators(dx, period)

    # Normalize ADX by dividing by period to get final values
    adx = adx / period

    return pd.Series(adx, index=high.index, name='adx')


def calculate_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate rolling volatility (standard deviation of returns).

    Args:
        close: Close prices
        period: Lookback period

    Returns:
        Series of volatility values (annualized percentage)
    """
    returns = close.pct_change()
    volatility = returns.rolling(window=period).std()

    # Annualize volatility (assuming 252 trading days, adjust for intraday)
    # For simplicity, just scale by sqrt(period) to normalize
    volatility_scaled = volatility * np.sqrt(period) * 100  # Convert to percentage

    return volatility_scaled.fillna(0)


def calculate_momentum(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate price momentum (rate of change).

    Args:
        close: Close prices
        period: Lookback period

    Returns:
        Series of momentum values (percentage change)
    """
    momentum = ((close - close.shift(period)) / close.shift(period)) * 100
    return momentum.fillna(0)


def calculate_range_compression(high: pd.Series, low: pd.Series, close: pd.Series,
                                atr_period: int = 14, compression_period: int = 20) -> pd.Series:
    """
    Calculate range compression (ATR relative to price).

    Lower values indicate range compression, which often precedes breakouts.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        atr_period: Period for ATR calculation
        compression_period: Period for compression ratio calculation

    Returns:
        Series of range compression ratios (%)
    """
    # Calculate ATR
    tr = calculate_true_range(high.values, low.values, close.values)
    atr = calculate_atr(tr, atr_period)
    atr_series = pd.Series(atr, index=high.index)

    # Calculate range compression as ATR / price ratio
    compression = (atr_series / close) * 100

    # Compare current compression to recent average
    avg_compression = compression.rolling(window=compression_period).mean()
    compression_ratio = compression / avg_compression

    return compression_ratio.fillna(1.0)


# ============================================================================
# Regime Classification
# ============================================================================

def classify_regime(adx: float, volatility: float, momentum: float,
                   range_compression: float, thresholds: Optional[Dict[str, float]] = None) -> str:
    """
    Classify market regime based on multiple indicators.

    Classification logic:
    - Trending: High ADX (>25) with directional momentum
    - Mean-reverting: Low ADX (<20), high volatility, range-bound
    - Choppy: Low ADX (<20), low volatility, no clear direction

    Args:
        adx: ADX value (trend strength)
        volatility: Volatility value
        momentum: Momentum value
        range_compression: Range compression ratio
        thresholds: Optional custom thresholds

    Returns:
        Regime label: 'trending', 'mean_reverting', or 'choppy'
    """
    # Default thresholds
    if thresholds is None:
        thresholds = {
            'adx_high': 25.0,
            'adx_low': 20.0,
            'volatility_high': 2.0,
            'volatility_low': 1.0,
            'momentum_threshold': 2.0,
            'compression_high': 1.2,
            'compression_low': 0.8
        }

    # Strong trend detection
    if adx > thresholds['adx_high'] and abs(momentum) > thresholds['momentum_threshold']:
        return 'trending'

    # Mean-reverting market (high volatility, range-bound)
    if adx < thresholds['adx_low'] and volatility > thresholds['volatility_high']:
        # Check if we're in a range (compression)
        if range_compression < thresholds['compression_high']:
            return 'mean_reverting'

    # Choppy market (low ADX, low volatility)
    if adx < thresholds['adx_low'] and volatility < thresholds['volatility_high']:
        return 'choppy'

    # Default to choppy if no clear regime
    return 'choppy'


def detect_regime(data: pd.DataFrame,
                 lookback: int = 100,
                 adx_period: int = 14,
                 volatility_period: int = 20,
                 momentum_period: int = 20,
                 thresholds: Optional[Dict[str, float]] = None) -> pd.Series:
    """
    Detect market regime from OHLCV data.

    Main entry point for regime detection. Returns a series with regime labels
    for each bar in the input data.

    Args:
        data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        lookback: Minimum bars needed for regime detection (default 100)
        adx_period: Period for ADX calculation (default 14)
        volatility_period: Period for volatility calculation (default 20)
        momentum_period: Period for momentum calculation (default 20)
        thresholds: Optional custom thresholds for regime classification

    Returns:
        Series with regime labels: 'trending', 'mean_reverting', 'choppy'

    Raises:
        ValueError: If data is insufficient or missing required columns
    """
    # Validate input
    required_columns = ['open', 'high', 'low', 'close']
    missing_cols = [col for col in required_columns if col not in data.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    if len(data) < lookback:
        raise ValueError(f"Insufficient data: {len(data)} bars, need at least {lookback}")

    # Normalize column names to lowercase
    data_lower = data.copy()
    data_lower.columns = data_lower.columns.str.lower()

    logger.info(f"Detecting regime for {len(data)} bars (lookback={lookback})")

    # Calculate indicators
    logger.debug("Calculating ADX...")
    adx = calculate_adx(data_lower['high'], data_lower['low'], data_lower['close'], period=adx_period)

    logger.debug("Calculating volatility...")
    volatility = calculate_volatility(data_lower['close'], period=volatility_period)

    logger.debug("Calculating momentum...")
    momentum = calculate_momentum(data_lower['close'], period=momentum_period)

    logger.debug("Calculating range compression...")
    range_compression = calculate_range_compression(
        data_lower['high'], data_lower['low'], data_lower['close'],
        atr_period=adx_period
    )

    # Classify regime for each bar
    logger.debug("Classifying regimes...")
    regimes = []
    for i in range(len(data)):
        if i < lookback:
            # Not enough data for classification
            regimes.append('unknown')
        else:
            regime = classify_regime(
                adx.iloc[i],
                volatility.iloc[i],
                momentum.iloc[i],
                range_compression.iloc[i],
                thresholds=thresholds
            )
            regimes.append(regime)

    regime_series = pd.Series(regimes, index=data.index, name='regime')

    # Log regime distribution
    regime_counts = regime_series.value_counts()
    logger.info(f"Regime distribution: {regime_counts.to_dict()}")

    return regime_series


def detect_regime_with_indicators(data: pd.DataFrame,
                                  lookback: int = 100,
                                  **kwargs) -> pd.DataFrame:
    """
    Detect regime and return all indicators for analysis.

    Useful for debugging and understanding regime classification decisions.

    Args:
        data: DataFrame with OHLCV data
        lookback: Minimum bars needed for regime detection
        **kwargs: Additional parameters passed to detect_regime()

    Returns:
        DataFrame with columns: regime, adx, volatility, momentum, range_compression
    """
    data_lower = data.copy()
    data_lower.columns = data_lower.columns.str.lower()

    # Get regime classification
    regime = detect_regime(data, lookback=lookback, **kwargs)

    # Calculate all indicators
    adx_period = kwargs.get('adx_period', 14)
    volatility_period = kwargs.get('volatility_period', 20)
    momentum_period = kwargs.get('momentum_period', 20)

    adx = calculate_adx(data_lower['high'], data_lower['low'], data_lower['close'], period=adx_period)
    volatility = calculate_volatility(data_lower['close'], period=volatility_period)
    momentum = calculate_momentum(data_lower['close'], period=momentum_period)
    range_compression = calculate_range_compression(
        data_lower['high'], data_lower['low'], data_lower['close'], atr_period=adx_period
    )

    # Combine into single DataFrame
    result = pd.DataFrame({
        'regime': regime,
        'adx': adx,
        'volatility': volatility,
        'momentum': momentum,
        'range_compression': range_compression
    }, index=data.index)

    return result


def filter_by_regime(data: pd.DataFrame, regime: str,
                    lookback: int = 100, **kwargs) -> pd.DataFrame:
    """
    Filter data to only include bars in a specific regime.

    Useful for regime-specific strategy testing and analysis.

    Args:
        data: DataFrame with OHLCV data
        regime: Target regime ('trending', 'mean_reverting', 'choppy')
        lookback: Minimum bars needed for regime detection
        **kwargs: Additional parameters passed to detect_regime()

    Returns:
        DataFrame filtered to only include bars in the specified regime
    """
    regimes = detect_regime(data, lookback=lookback, **kwargs)
    mask = regimes == regime
    filtered_data = data[mask].copy()

    logger.info(f"Filtered to {len(filtered_data)} bars in '{regime}' regime "
               f"({len(filtered_data)/len(data)*100:.1f}% of total)")

    return filtered_data


def calculate_regime_statistics(data: pd.DataFrame, regime_series: pd.Series) -> Dict[str, Dict]:
    """
    Calculate statistics for each regime period.

    Args:
        data: DataFrame with OHLCV data
        regime_series: Series with regime labels

    Returns:
        Dictionary with statistics for each regime type
    """
    data_lower = data.copy()
    data_lower.columns = data_lower.columns.str.lower()

    stats = {}

    for regime in ['trending', 'mean_reverting', 'choppy']:
        mask = regime_series == regime
        regime_data = data_lower[mask]

        if len(regime_data) > 0:
            returns = regime_data['close'].pct_change()

            stats[regime] = {
                'count': len(regime_data),
                'percentage': len(regime_data) / len(data) * 100,
                'mean_return': returns.mean() * 100,
                'volatility': returns.std() * 100,
                'sharpe': returns.mean() / returns.std() if returns.std() > 0 else 0,
                'max_drawdown': (regime_data['close'] / regime_data['close'].cummax() - 1).min() * 100
            }
        else:
            stats[regime] = {
                'count': 0,
                'percentage': 0,
                'mean_return': 0,
                'volatility': 0,
                'sharpe': 0,
                'max_drawdown': 0
            }

    return stats


# ============================================================================
# Integration Helpers
# ============================================================================

def add_regime_to_data(data: pd.DataFrame, lookback: int = 100, **kwargs) -> pd.DataFrame:
    """
    Add regime column to existing OHLCV data.

    Convenience function for adding regime detection to data pipeline.

    Args:
        data: DataFrame with OHLCV data
        lookback: Minimum bars needed for regime detection
        **kwargs: Additional parameters passed to detect_regime()

    Returns:
        DataFrame with added 'regime' column
    """
    data_with_regime = data.copy()
    data_with_regime['regime'] = detect_regime(data, lookback=lookback, **kwargs)
    return data_with_regime


if __name__ == "__main__":
    # Quick test of regime detector
    print("Testing Market Regime Detector...")

    from data_loader import create_synthetic_data

    # Create test data
    test_data = create_synthetic_data(bars=5000, symbol="ES")
    print(f"Created {len(test_data)} bars of test data")

    # Detect regimes
    regimes = detect_regime(test_data, lookback=100)
    print(f"\nRegime distribution:")
    print(regimes.value_counts())

    # Get detailed indicators
    detailed = detect_regime_with_indicators(test_data, lookback=100)
    print(f"\nDetailed indicators (last 5 bars):")
    print(detailed.tail())

    # Calculate regime statistics
    stats = calculate_regime_statistics(test_data, regimes)
    print(f"\nRegime statistics:")
    for regime, metrics in stats.items():
        print(f"\n{regime.upper()}:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.2f}")

    print("\nRegime detector test complete!")
