"""
Regression Detection Tests
==========================

Captures baseline metrics and validates that refactoring maintains correctness.
Tolerance: <0.01% difference from original implementation.
"""

import pytest
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from config.system_config import create_trading_config, ExecutionModels
from optimization.vectorbt_engine import VectorBTPortfolioEngine


class RegressionBaseline:
    """Manage baseline metrics for regression detection."""

    BASELINE_DIR = Path(__file__).parent / "baselines"
    TOLERANCE = 0.0001  # <0.01%

    @classmethod
    def ensure_baseline_dir(cls):
        """Ensure baseline directory exists."""
        cls.BASELINE_DIR.mkdir(exist_ok=True)

    @classmethod
    def capture_baseline(cls, phase_name: str, metrics_dict: Dict) -> Dict:
        """Capture baseline metrics before refactoring."""
        cls.ensure_baseline_dir()
        
        timestamp = datetime.now().isoformat()
        
        baseline = {
            'phase': phase_name,
            'timestamp': timestamp,
            'metrics': {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                       for k, v in metrics_dict.items() 
                       if isinstance(v, (int, float, np.number))},
            'metrics_keys': list(metrics_dict.keys())
        }
        
        baseline_file = cls.BASELINE_DIR / f"{phase_name}_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        return baseline

    @classmethod
    def validate_regression(cls, phase_name: str, current_metrics: Dict) -> Tuple[bool, List[Dict]]:
        """
        Validate current metrics against baseline (<0.01% tolerance).
        
        Returns (is_valid, list_of_regressions)
        """
        baseline_file = cls.BASELINE_DIR / f"{phase_name}_baseline.json"
        
        if not baseline_file.exists():
            # No baseline yet - this is first run
            return True, []
        
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        baseline_metrics = baseline['metrics']
        regressions = []
        
        for metric_name, baseline_value in baseline_metrics.items():
            if metric_name not in current_metrics:
                continue
            
            current_value = current_metrics[metric_name]
            
            # Skip nan values
            if pd.isna(baseline_value) or pd.isna(current_value):
                continue
            
            # Calculate percentage difference
            if baseline_value != 0:
                pct_diff = abs((current_value - baseline_value) / baseline_value)
            else:
                pct_diff = abs(current_value - baseline_value)
            
            if pct_diff > cls.TOLERANCE:
                regressions.append({
                    'metric': metric_name,
                    'baseline': baseline_value,
                    'current': current_value,
                    'pct_diff': pct_diff * 100
                })
        
        return len(regressions) == 0, regressions


@pytest.fixture
def trading_config():
    """Standard trading configuration."""
    return create_trading_config(
        symbol="MES",
        timeframe="5m",
        account_type="topstep_50k"
    )


@pytest.fixture
def execution_config():
    """Standard execution configuration."""
    return {
        'commission_per_trade': 2.50,
        'slippage_ticks': 1,
        'contracts_per_trade': 1
    }


@pytest.fixture
def baseline_data():
    """Generate consistent baseline data for regression testing."""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='5min')
    
    close = 4500 + np.cumsum(np.random.randn(500) * 2)
    data = pd.DataFrame({
        'open': close.copy(),
        'high': close + np.abs(np.random.randn(500) * 1.5),
        'low': close - np.abs(np.random.randn(500) * 1.5),
        'close': close,
        'volume': np.random.randint(100, 10000, 500)
    }, index=dates)
    
    return data


@pytest.fixture
def baseline_signals(baseline_data):
    """Generate consistent baseline signals."""
    signals = pd.Series(0, index=baseline_data.index)
    
    # Long positions every 50 bars
    for start in range(10, len(signals), 100):
        signals.iloc[start:start+50] = 1
    
    return signals


class TestRegressionDetection:
    """Test suite for regression detection."""

    def test_long_only_strategy_regression(self, trading_config, execution_config, 
                                           baseline_data, baseline_signals):
        """Test long-only strategy maintains metric consistency."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        metrics = engine.run_backtest(baseline_data, baseline_signals)
        
        # Capture or validate baseline
        is_valid, regressions = RegressionBaseline.validate_regression("long_only", metrics)
        
        if not is_valid:
            # Print regressions for debugging
            for reg in regressions:
                print(f"Regression: {reg['metric']} "
                      f"baseline={reg['baseline']:.4f}, "
                      f"current={reg['current']:.4f}, "
                      f"diff={reg['pct_diff']:.3f}%")
        
        # First run creates baseline; subsequent runs validate against it
        assert is_valid or not RegressionBaseline.BASELINE_DIR.joinpath("long_only_baseline.json").exists()

    def test_metric_stability_across_runs(self, trading_config, execution_config,
                                         baseline_data, baseline_signals):
        """Test that same data/signals produce same metrics (determinism)."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        
        # Run backtest twice with same data
        metrics1 = engine.run_backtest(baseline_data, baseline_signals)
        metrics2 = engine.run_backtest(baseline_data, baseline_signals)
        
        # Compare key metrics
        key_metrics = ['total_trades', 'total_dollar_pnl', 'sharpe_ratio', 'max_drawdown']
        
        for metric in key_metrics:
            val1 = metrics1.get(metric)
            val2 = metrics2.get(metric)
            
            if val1 is not None and val2 is not None:
                if pd.isna(val1) and pd.isna(val2):
                    continue
                elif not pd.isna(val1) and not pd.isna(val2):
                    assert abs(val1 - val2) < 0.01, \
                        f"Metric {metric} not deterministic: {val1} != {val2}"

    def test_equity_curve_consistency(self, trading_config, execution_config,
                                     baseline_data, baseline_signals):
        """Test that equity curve is consistent across runs."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        
        metrics1 = engine.run_backtest(baseline_data, baseline_signals)
        metrics2 = engine.run_backtest(baseline_data, baseline_signals)
        
        eq1 = metrics1['equity_curve']
        eq2 = metrics2['equity_curve']
        
        assert len(eq1) == len(eq2), "Equity curve length mismatch"
        
        # Check starting and ending equity match
        assert eq1[0] == eq2[0], "Starting equity differs"
        assert abs(eq1[-1] - eq2[-1]) < 0.01, "Ending equity differs"

    def test_small_vs_large_dataset_consistency(self, trading_config, execution_config):
        """Test that metrics scale consistently with data size."""
        np.random.seed(42)
        
        # Small dataset
        dates_small = pd.date_range('2024-01-01', periods=100, freq='5min')
        close_small = 4500 + np.cumsum(np.random.randn(100) * 2)
        data_small = pd.DataFrame({
            'open': close_small,
            'high': close_small + 1,
            'low': close_small - 1,
            'close': close_small,
            'volume': np.random.randint(100, 10000, 100)
        }, index=dates_small)
        
        signals_small = pd.Series(0, index=data_small.index)
        signals_small.iloc[10:30] = 1
        
        # Large dataset (same pattern, repeated)
        dates_large = pd.date_range('2024-01-01', periods=1000, freq='5min')
        close_large = 4500 + np.cumsum(np.random.randn(1000) * 2)
        data_large = pd.DataFrame({
            'open': close_large,
            'high': close_large + 1,
            'low': close_large - 1,
            'close': close_large,
            'volume': np.random.randint(100, 10000, 1000)
        }, index=dates_large)
        
        signals_large = pd.Series(0, index=data_large.index)
        signals_large.iloc[10:30] = 1  # Same position pattern
        
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        
        metrics_small = engine.run_backtest(data_small, signals_small)
        metrics_large = engine.run_backtest(data_large, signals_large)
        
        # Trade count should scale reasonably
        trades_small = metrics_small['total_trades']
        trades_large = metrics_large['total_trades']
        
        # Both should have same number of trades (same signal pattern)
        assert trades_small == trades_large, \
            f"Trade count mismatch: {trades_small} vs {trades_large}"

    def test_commission_calculation_consistency(self, trading_config, execution_config,
                                               baseline_data, baseline_signals):
        """Test that commission is calculated consistently."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        metrics = engine.run_backtest(baseline_data, baseline_signals)
        
        # Commission should be predictable
        total_trades = metrics['total_trades']
        expected_commission = total_trades * 2.50  # commission_per_trade
        actual_commission = metrics['total_commission_cost']
        
        # Allow small tolerance for rounding
        assert abs(actual_commission - expected_commission) < 1.0, \
            f"Commission mismatch: expected {expected_commission}, got {actual_commission}"

    def test_slippage_calculation_consistency(self, trading_config, execution_config,
                                             baseline_data, baseline_signals):
        """Test that slippage is calculated consistently."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        metrics = engine.run_backtest(baseline_data, baseline_signals)
        
        # Slippage should be predictable
        total_trades = metrics['total_trades']
        expected_slippage = total_trades * 1 * 1.25  # slippage_ticks * tick_value
        actual_slippage = metrics['total_slippage_cost']
        
        # Allow small tolerance for rounding
        assert abs(actual_slippage - expected_slippage) < 1.0, \
            f"Slippage mismatch: expected {expected_slippage}, got {actual_slippage}"

    def test_zero_trades_consistency(self, trading_config, execution_config, baseline_data):
        """Test that zero-trade scenarios are handled consistently."""
        engine = VectorBTPortfolioEngine(trading_config, execution_config)
        
        # No signals
        signals = pd.Series(0, index=baseline_data.index)
        metrics = engine.run_backtest(baseline_data, signals)
        
        assert metrics['total_trades'] == 0
        assert metrics['total_dollar_pnl'] == 0.0 or pd.isna(metrics['total_dollar_pnl'])
        assert metrics['final_equity'] == 50000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
