"""
Bollinger Band Squeeze Indicator Calculations (CPU-only)

Implements the TTM Squeeze methodology with Bollinger Bands, Keltner Channels,
momentum oscillator, and breakout detection for futures trading using
numpy/pandas only (no GPU / PyTorch dependency).
"""
import pandas as pd
import numpy as np


def calculate_bollinger_bands(data: pd.Series, period: int, std_dev: float):
    """Calculate Bollinger Bands using EMA for middle band and rolling std.

    Returns a tuple of (upper_band, middle_band, lower_band).
    """
    middle_band = data.ewm(span=period, adjust=False).mean()
    std = data.rolling(window=period).std(ddof=1)
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return upper_band, middle_band, lower_band


def calculate_keltner_channels(df: pd.DataFrame, period: int, atr_multiplier: float):
    """Calculate Keltner Channels using ATR (EMA-based)."""
    middle_channel = df['close'].ewm(span=period, adjust=False).mean()
    atr = calculate_atr(df, period)
    upper_channel = middle_channel + (atr * atr_multiplier)
    lower_channel = middle_channel - (atr * atr_multiplier)
    return upper_channel, middle_channel, lower_channel


def calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Average True Range using EMA smoothing."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(span=period, adjust=False).mean()


def detect_squeeze(bb_upper: pd.Series, bb_lower: pd.Series, kc_upper: pd.Series, kc_lower: pd.Series) -> pd.Series:
    """Detect when Bollinger Bands are inside Keltner Channels (squeeze)."""
    return (bb_upper < kc_upper) & (bb_lower > kc_lower)


def calculate_momentum_oscillator(df: pd.DataFrame, period: int) -> pd.Series:
    """Linear-regression slope of close over rolling window as momentum."""
    close = df['close']

    def linreg_slope(series: pd.Series) -> float:
        n = len(series)
        if n < 2:
            return 0.0
        x = np.arange(n)
        # slope via least squares
        x_mean = x.mean()
        y = series.values
        y_mean = y.mean()
        denom = ((x - x_mean) ** 2).sum()
        if denom == 0:
            return 0.0
        num = ((x - x_mean) * (y - y_mean)).sum()
        return float(num / denom)

    return close.rolling(window=period).apply(linreg_slope, raw=False)


def calculate_donchian_channels(df: pd.DataFrame, period: int):
    """Donchian Channels: highest high and lowest low over window."""
    upper = df['high'].rolling(window=period).max()
    lower = df['low'].rolling(window=period).min()
    return upper, lower


def calculate_squeeze_duration(squeeze_signal: pd.Series) -> pd.Series:
    """Count consecutive bars where squeeze_signal is True."""
    groups = (squeeze_signal != squeeze_signal.shift(1)).cumsum()
    duration = squeeze_signal.groupby(groups).cumsum()
    return duration.where(squeeze_signal, 0)


def calculate_volume_ratio(df: pd.DataFrame, period: int) -> pd.Series:
    """Volume compared to rolling average; NaNs default to 1.0."""
    avg_volume = df['volume'].rolling(window=period).mean()
    ratio = df['volume'] / avg_volume
    return ratio.fillna(1.0)


def calculate_all_indicators(data: pd.DataFrame, params: dict, use_gpu: bool | None = None) -> dict:
    """CPU-only indicator calculation for Bollinger Squeeze strategy."""
    indicators: dict[str, pd.Series] = {}

    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
        data['close'], params['bb_period'], params['bb_std_dev']
    )
    indicators['bb_upper'] = bb_upper
    indicators['bb_middle'] = bb_middle
    indicators['bb_lower'] = bb_lower

    kc_upper, kc_middle, kc_lower = calculate_keltner_channels(
        data, params['kc_period'], params['kc_atr_multiplier']
    )
    indicators['kc_upper'] = kc_upper
    indicators['kc_middle'] = kc_middle
    indicators['kc_lower'] = kc_lower

    indicators['squeeze'] = detect_squeeze(bb_upper, bb_lower, kc_upper, kc_lower)
    indicators['squeeze_duration'] = calculate_squeeze_duration(indicators['squeeze'])
    indicators['momentum'] = calculate_momentum_oscillator(data, params['momentum_period'])

    breakout_upper, breakout_lower = calculate_donchian_channels(data, params['breakout_period'])
    indicators['breakout_upper'] = breakout_upper
    indicators['breakout_lower'] = breakout_lower

    exit_upper, exit_lower = calculate_donchian_channels(data, params['exit_donchian_period'])
    indicators['exit_upper'] = exit_upper
    indicators['exit_lower'] = exit_lower

    indicators['atr'] = calculate_atr(data, params['atr_period'])

    if params.get('use_trend_filter'):
        indicators['trend_filter'] = data['close'].ewm(
            span=params['trend_filter_period'], adjust=False
        ).mean()

    if params.get('volume_filter'):
        indicators['volume_ratio'] = calculate_volume_ratio(data, params['bb_period'])

    return indicators

