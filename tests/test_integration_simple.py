"""
Simple end-to-end validation test for VectorBT integration.
Tests the actual integration without heavy dependencies.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import pytest

# Add TopStepB to path dynamically
project_root = Path(__file__).parent.parent / "TopStepB"
sys.path.insert(0, str(project_root))

from optimization.vectorbt_engine import VectorBTPortfolioEngine, IndicatorCache
from optimization.strategy_schema import StrategySchema, ParameterDef, ParameterType
from optimization.performance_monitor import PerformanceMonitor
from config.system_config import MarketSpec, TradingConfig, create_trading_config
from strategies.base import BaseStrategy


@pytest.fixture
def trading_config():
    """Create trading configuration for tests."""
    return create_trading_config(
        symbol="MES",
        timeframe="5m",
        account_type="topstep_50k"
    )


@pytest.fixture
def execution_config():
    """Create execution configuration for tests."""
    return {
        'commission_per_trade': 0.62,
        'slippage_ticks': 1
    }


@pytest.fixture
def test_data():
    """Generate test data for backtesting."""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='5min')
    closes = 4500 + np.cumsum(np.random.randn(1000) * 0.5)

    data = pd.DataFrame({
        'open': closes,
        'high': closes + 1,
        'low': closes - 1,
        'close': closes,
        'volume': np.random.randint(100, 1000, 1000)
    }, index=dates)

    return data


@pytest.fixture
def simple_strategy(trading_config):
    """Create a simple test strategy."""
    class SimpleTestStrategy(BaseStrategy):
        @property
        def name(self):
            return "simple_test"

        @property
        def description(self):
            return "Simple test strategy"

        @property
        def category(self):
            return "test"

        @property
        def min_data_points(self):
            return 50

        def generate_signals(self, data, params, config):
            sma = data['close'].rolling(params.get('period', 20)).mean()
            signals = pd.Series(0, index=data.index)
            signals[data['close'] > sma] = 1
            return signals.shift(1).fillna(0)

        def reset_state(self):
            pass

        def get_parameter_ranges(self):
            return {'period': (10, 50, 1)}

        def validate_parameters(self, params):
            return True

        def get_strategy_metadata(self):
            return {'name': self.name}

    strategy = SimpleTestStrategy(name="simple_test")
    strategy.set_config(trading_config)
    return strategy


def test_imports():
    """Test that all components import successfully."""
    # If we got here, imports already succeeded
    assert VectorBTPortfolioEngine is not None
    assert IndicatorCache is not None
    assert StrategySchema is not None
    assert PerformanceMonitor is not None


def test_configuration_creation(trading_config, execution_config):
    """Test that configuration is created successfully."""
    assert trading_config is not None
    assert execution_config is not None
    assert 'commission_per_trade' in execution_config
    assert execution_config['commission_per_trade'] == 0.62


def test_data_generation(test_data):
    """Test that test data is generated correctly."""
    assert len(test_data) == 1000
    assert 'close' in test_data.columns
    assert 'open' in test_data.columns
    assert 'high' in test_data.columns
    assert 'low' in test_data.columns
    assert 'volume' in test_data.columns


def test_strategy_creation(simple_strategy):
    """Test that strategy is created successfully."""
    assert simple_strategy is not None
    assert simple_strategy.name == "simple_test"
    assert simple_strategy.min_data_points == 50


def test_signal_generation(simple_strategy, test_data):
    """Test that trading signals are generated correctly."""
    params = {'period': 20}
    signals = simple_strategy.execute_strategy(test_data, params)

    num_longs = (signals == 1).sum()
    num_shorts = (signals == -1).sum()
    num_flat = (signals == 0).sum()

    # Verify we have signals
    assert len(signals) == len(test_data)
    assert num_longs >= 0
    assert num_shorts >= 0
    assert num_flat >= 0
    assert num_longs + num_shorts + num_flat == len(test_data)


def test_vectorbt_backtest(test_data, simple_strategy, trading_config, execution_config):
    """Test that VectorBT backtest runs successfully."""
    params = {'period': 20}
    signals = simple_strategy.execute_strategy(test_data, params)

    engine = VectorBTPortfolioEngine(trading_config, execution_config)
    metrics = engine.run_backtest(test_data, signals, contracts_per_trade=1)

    # Verify metrics exist
    assert metrics is not None
    assert 'total_trades' in metrics
    assert 'total_dollar_pnl' in metrics
    assert 'win_rate' in metrics
    assert 'sharpe_ratio' in metrics
    assert 'profit_factor' in metrics
    assert 'max_drawdown_dollars' in metrics
    assert 'final_equity' in metrics

    # Verify metrics are reasonable
    assert metrics['total_trades'] >= 0
    assert isinstance(metrics['total_dollar_pnl'], (int, float))
    assert 0 <= metrics['win_rate'] <= 100
    assert isinstance(metrics['sharpe_ratio'], (int, float))
    assert metrics['profit_factor'] >= 0
    assert metrics['max_drawdown_dollars'] <= 0


def test_indicator_caching(test_data):
    """Test that indicator caching works correctly."""
    cache = IndicatorCache(test_data)

    # Add indicators
    cache.add_indicator('sma_20', lambda df: df['close'].rolling(20).mean())
    cache.add_indicator('sma_50', lambda df: df['close'].rolling(50).mean())

    # Retrieve multiple times
    for _ in range(10):
        sma = cache.get('sma_20')
        assert sma is not None

    stats = cache.get_stats()
    assert 'cached_indicators' in stats
    assert 'total_hits' in stats
    assert stats['cached_indicators'] >= 2
    assert stats['total_hits'] >= 10


def test_strategy_schema():
    """Test that strategy schema works correctly."""
    schema = StrategySchema(
        strategy_name="test_strategy",
        strategy_class="TestStrategy",
        description="Test",
        category="test"
    )

    schema.add_parameter(ParameterDef(
        name="period",
        param_type=ParameterType.INT,
        default=20,
        min_value=10,
        max_value=50
    ))

    # Test JSON export
    json_str = schema.to_json()
    assert json_str is not None
    assert len(json_str) > 0
    assert len(schema.parameters) == 1


def test_performance_monitoring(test_data):
    """Test that performance monitoring works correctly."""
    monitor = PerformanceMonitor()

    with monitor.track('test_operation'):
        # Simulate some work
        _ = test_data['close'].rolling(50).mean()

    summary = monitor.get_summary()
    assert len(summary) >= 1
    assert 'test_operation' in summary
    assert 'count' in summary['test_operation']
    assert 'total_time' in summary['test_operation']
    assert summary['test_operation']['count'] == 1


def test_metrics_format(test_data, simple_strategy, trading_config, execution_config):
    """Test that all required metrics are present in the output."""
    params = {'period': 20}
    signals = simple_strategy.execute_strategy(test_data, params)

    engine = VectorBTPortfolioEngine(trading_config, execution_config)
    metrics = engine.run_backtest(test_data, signals, contracts_per_trade=1)

    required_metrics = [
        'total_dollar_pnl', 'total_return_percentage', 'sharpe_ratio',
        'profit_factor', 'win_rate', 'total_trades', 'max_drawdown_dollars',
        'total_commission_cost', 'total_slippage_cost', 'equity_curve',
        'daily_pnl', 'final_equity'
    ]

    missing = [m for m in required_metrics if m not in metrics]
    assert len(missing) == 0, f"Missing metrics: {missing}"
    assert len(metrics) >= len(required_metrics)
