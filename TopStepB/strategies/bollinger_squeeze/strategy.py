"""
Bollinger Band Squeeze Breakout Strategy Implementation (CPU-only)

A volatility-based breakout strategy using the TTM Squeeze methodology.
Identifies low volatility periods (squeeze) and trades the subsequent breakouts.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Union, Tuple, List

from ..base import BaseStrategy
from config.system_config import TradingConfig
from .indicators import calculate_all_indicators
from .parameters import get_default_parameters, get_parameter_ranges, validate_parameters


class BollingerSqueezeStrategy(BaseStrategy):
    """
    Bollinger Band Squeeze breakout strategy for futures trading.
    
    This strategy implements the TTM Squeeze methodology:
    - Identifies periods when Bollinger Bands are inside Keltner Channels (squeeze)
    - Waits for momentum confirmation and breakout
    - Enters in the direction of the breakout with proper risk management
    - Uses multiple exit methods for optimal trade management
    """
    
    # Required class attributes
    name = "bollinger_squeeze"
    description = "TTM Squeeze breakout strategy using Bollinger Bands and Keltner Channels"
    category = "breakout"
    min_data_points = 250  # Need enough for trend filter and indicators
    
    def __init__(self):
        """Initialize strategy following BaseStrategy contract."""
        super().__init__(self.name)
        
        # Add debug logger for signal timing validation
        from utils.logger import get_logger
        self._debug_logger = get_logger(f"signal_timing_{self.name}")
    
    def generate_signals(self, data: pd.DataFrame, params: Dict[str, Any], config: TradingConfig) -> pd.Series:
        """
        Generate trading signals based on Bollinger Band squeeze and breakout.
        
        Args:
            data: OHLCV DataFrame with datetime index
            params: Strategy parameters dictionary
            config: TradingConfig for market specifications and account settings
            
        Returns:
            pd.Series: Trading signals (-1, 0, 1) with proper position holding
        """
        
        # Validate inputs
        if not self.validate_parameters(params):
            raise ValueError("Invalid parameters")
        
        self.validate_data(data)
        
        # Calculate all indicators (CPU-only)
        indicators = calculate_all_indicators(data, params, use_gpu=None)
        
        # Phase 1: Generate entry conditions (vectorized for performance)
        entry_signals = self._generate_entry_signals_vectorized(data, indicators, params)
        
        # Phase 2: Apply stateful position management (mirrors deployment)
        final_signals = self._apply_stateful_position_management(data, entry_signals, indicators, params)
        
        return final_signals
    
    def _generate_entry_signals_vectorized(self, data: pd.DataFrame, indicators: Dict, params: Dict[str, Any]) -> pd.Series:
        """Generate entry signals using vectorized operations."""
        
        # Initialize entry signals
        entry_signals = pd.Series(0, index=data.index)
        
        # Extract key data
        close = data['close']
        
        # Extract indicators
        squeeze = indicators['squeeze']
        momentum = indicators['momentum']
        breakout_upper = indicators['breakout_upper']
        breakout_lower = indicators['breakout_lower']
        
        # Momentum conditions
        if params['use_momentum_filter']:
            momentum_bullish = momentum > params['momentum_threshold']
            momentum_bearish = momentum < -params['momentum_threshold']
        else:
            momentum_bullish = pd.Series(True, index=data.index)
            momentum_bearish = pd.Series(True, index=data.index)
        
        # Trend filter conditions
        if params['use_trend_filter']:
            trend_filter = indicators['trend_filter']
            long_trend = close > trend_filter
            short_trend = close < trend_filter
        else:
            long_trend = pd.Series(True, index=data.index)
            short_trend = pd.Series(True, index=data.index)
        
        # Volume filter conditions
        if params['volume_filter']:
            volume_ratio = indicators['volume_ratio']
            volume_ok = volume_ratio >= params['min_volume_ratio']
        else:
            volume_ok = pd.Series(True, index=data.index)
        
        # Breakout conditions
        long_breakout = close > breakout_upper.shift(1)
        short_breakout = close < breakout_lower.shift(1)
        
        # Check if squeeze was active on previous bar AND minimum duration met
        squeeze_setup = squeeze.shift(1)
        squeeze_duration = indicators['squeeze_duration']
        squeeze_ready = squeeze_duration.shift(1) >= params['min_squeeze_bars']  # CRITICAL FIX
        
        # Generate entry conditions
        long_entry = (
            squeeze_setup &                    # Squeeze was active
            squeeze_ready &                    # CRITICAL: Minimum squeeze duration met
            long_breakout &                    # Breakout to upside
            momentum_bullish &                 # Momentum confirmation
            long_trend &                       # Trend filter
            volume_ok                          # Volume confirmation
        )
        
        short_entry = (
            squeeze_setup &                    # Squeeze was active
            squeeze_ready &                    # CRITICAL: Minimum squeeze duration met
            short_breakout &                   # Breakout to downside
            momentum_bearish &                 # Momentum confirmation
            short_trend &                      # Trend filter
            volume_ok                          # Volume confirmation
        )
        
        # Set entry signals
        entry_signals[long_entry] = 1
        entry_signals[short_entry] = -1
        
        return entry_signals
    
    def _apply_stateful_position_management(self, data: pd.DataFrame, entry_signals: pd.Series,
                                            indicators: Dict, params: Dict[str, Any]) -> pd.Series:
        """Apply stateful position management using a simple CPU loop."""

        # Initialize final signals
        final_signals = np.zeros(len(data), dtype=np.int8)

        # State variables (identical semantics to deployment template)
        position: int = 0
        entry_price: float = 0.0
        stop_loss: float = 0.0
        target_price: float = 0.0
        bars_in_trade: int = 0
        bars_since_exit: int = 0

        # Convert price data and inputs to numpy
        close_prices = data['close'].to_numpy(dtype=float)
        opens = data['open'].to_numpy(dtype=float)
        entry_arr = entry_signals.to_numpy(dtype=np.int8)

        # Pre-extract indicators for all exit methods
        atr = indicators['atr'].to_numpy(dtype=float)

        if params['exit_method'] == 'trailing_donchian':
            exit_upper = indicators['exit_upper'].to_numpy(dtype=float)
            exit_lower = indicators['exit_lower'].to_numpy(dtype=float)
        elif params['exit_method'] == 'opposite_band':
            bb_upper = indicators['bb_upper'].to_numpy(dtype=float)
            bb_lower = indicators['bb_lower'].to_numpy(dtype=float)
        
        for i in range(1, len(data)):
            # --- In a position: Check for exits ---
            if position != 0:
                bars_in_trade += 1
                exit_triggered = False
                exit_reason = ""
                
                # PRIORITY 1: Stop-loss (most important) - matches deployment template
                if position == 1 and close_prices[i-1] <= stop_loss:
                    exit_triggered = True
                    exit_reason = "stop_loss_long"
                elif position == -1 and close_prices[i-1] >= stop_loss:
                    exit_triggered = True
                    exit_reason = "stop_loss_short"
                
                # PRIORITY 2: Exit method specific conditions (if no stop-loss hit)
                elif params['exit_method'] == 'fixed_rr':
                    if position == 1 and close_prices[i-1] >= target_price:
                        exit_triggered = True
                        exit_reason = "fixed_rr_long"
                    elif position == -1 and close_prices[i-1] <= target_price:
                        exit_triggered = True
                        exit_reason = "fixed_rr_short"
                        
                elif params['exit_method'] == 'trailing_donchian':
                    if position == 1 and close_prices[i-1] < exit_lower[i-1]:
                        exit_triggered = True
                        exit_reason = "trailing_donchian_long"
                    elif position == -1 and close_prices[i-1] > exit_upper[i-1]:
                        exit_triggered = True
                        exit_reason = "trailing_donchian_short"
                        
                elif params['exit_method'] == 'opposite_band':
                    if position == 1 and close_prices[i-1] >= bb_upper[i-1]:
                        exit_triggered = True
                        exit_reason = "opposite_band_long"
                    elif position == -1 and close_prices[i-1] <= bb_lower[i-1]:
                        exit_triggered = True
                        exit_reason = "opposite_band_short"
                
                if exit_triggered:
                    self._debug_logger.debug(f"Bar {i}: Exit triggered - {exit_reason}, bars_in_trade={bars_in_trade}")
                    position = 0
                    stop_loss = 0.0      # Reset exit levels
                    target_price = 0.0
                    bars_since_exit = 1
                    bars_in_trade = 0
                # else, hold position
            
            # --- Not in a position: Check for entries ---
            else:
                if bars_since_exit > 0:
                    bars_since_exit += 1
                
                # Check for entry
                if True:
                    entry_signal = int(entry_arr[i-1])

                    if entry_signal != 0:
                        position = entry_signal
                        # Entry at next bar's open (current bar index i)
                        entry_price = float(opens[i])

                        # Calculate stop-loss and target prices
                        if position == 1:  # Long
                            stop_loss = entry_price - (atr[i-1] * params['stop_loss_atr_multiplier'])
                            if params['exit_method'] == 'fixed_rr':
                                target_price = entry_price + (entry_price - stop_loss) * params['risk_reward_ratio']
                            else:
                                target_price = 0.0
                        else:  # Short
                            stop_loss = entry_price + (atr[i-1] * params['stop_loss_atr_multiplier'])
                            if params['exit_method'] == 'fixed_rr':
                                target_price = entry_price - (stop_loss - entry_price) * params['risk_reward_ratio']
                            else:
                                target_price = 0.0

                        bars_in_trade = 0
                        bars_since_exit = 0
                        entry_type = "long" if position == 1 else "short"
                        self._debug_logger.debug(
                            f"Bar {i}: {entry_type} entry at open price {entry_price}, stop: {stop_loss}, target: {target_price}"
                        )

            final_signals[i] = position

        return pd.Series(final_signals, index=data.index)
    
    def reset_state(self) -> None:
        """
        Reset internal strategy state to prevent contamination between calls.
        
        CRITICAL: This method resets all stateful variables used in the stateful loop iteration
        to prevent contamination between optimization trials. Called automatically by 
        execute_strategy() before each generate_signals() call.
        
        Stateful variables that must be reset:
        - position: Current position (0=flat, 1=long, -1=short)
        - entry_price: Price at which current position was entered
        - stop_loss: Current protective stop level
        - target_price: Profit target level when using fixed R:R
        - bars_in_trade: Number of bars since position entry
        - bars_since_exit: Number of bars since last position exit
        """
        # Initialize stateful attributes to their neutral defaults so repeated
        # executions of the same strategy instance start from a clean slate.
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.target_price = 0.0
        self.bars_in_trade = 0
        self.bars_since_exit = 0
    
    def get_parameter_ranges(self) -> Dict[str, Union[Tuple[Union[int, float], ...], List[str]]]:
        """Return parameter ranges for optimization."""
        return get_parameter_ranges()
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameter dictionary."""
        return validate_parameters(params)
    
    def define_constraints(self) -> Dict[str, Any]:
        """
        Return parameter constraints for optimization engine.
        
        Bollinger squeeze strategy constraints:
        - exit_donchian_period must be less than breakout_period for proper exit timing
        - breakout_period must be less than or equal to bb_period for valid Bollinger Band analysis
        """
        return {
            'comparison': [
                ('exit_donchian_period', '<', 'breakout_period'),
                ('breakout_period', '<=', 'bb_period')
            ]
        }
    
    def get_strategy_metadata(self) -> Dict[str, Any]:
        """Return strategy metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "min_data_points": self.min_data_points,
            "parameter_count": len(get_default_parameters()),
            "author": "TopStepX Team",
            "version": "1.0.0",
            "indicators_used": ["Bollinger Bands", "Keltner Channels", "ATR", "Donchian Channels", "Momentum"],
            "suitable_markets": ["Futures", "Stocks", "ETFs", "Forex"],
            "trading_style": "Volatility Breakout",
            "risk_profile": "Medium-High",
            "typical_holding_period": "Short to Medium Term",
            "methodology": "TTM Squeeze",
        }
