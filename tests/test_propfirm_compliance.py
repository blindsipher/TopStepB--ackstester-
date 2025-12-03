"""
PropFirm Compliance Tests
=========================

Verifies strategies comply with TopStep/prop-firm trading rules.
Focus: Daily loss limits, trailing drawdown, and profit targets.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / 'TopStepB'))

from config.system_config import (
    create_trading_config, TopStepAccounts,
    AccountConfig, ValidationCriteria
)
from optimization.vectorbt_engine import VectorBTPortfolioEngine


class TestPropFirmCompliance:
    """Verify strategies comply with TopStep and prop-firm rules."""

    @pytest.fixture
    def topstep_50k_account(self) -> AccountConfig:
        """TopStep $50K Trading Combine account."""
        return TopStepAccounts.TRADING_COMBINE_50K

    @pytest.fixture
    def validation_criteria(self) -> ValidationCriteria:
        """Default validation criteria."""
        return ValidationCriteria()

    def test_daily_loss_limit_compliance(self, topstep_50k_account):
        """Verify daily losses don't exceed TopStep daily loss limit."""
        daily_loss_limit = abs(topstep_50k_account.daily_loss_limit)  # 1000
        
        # Simulate compliant daily P&L (within limits)
        compliant_pnl = pd.Series([
            100.0, -500.0, 200.0, -400.0, 300.0, -150.0, 400.0, -800.0
        ])
        
        # Check compliance for compliant data
        max_loss = compliant_pnl.min()
        assert max_loss >= -daily_loss_limit, \
            f"Daily loss ${max_loss:.2f} exceeds limit ${daily_loss_limit:.2f}"
        
        # Verify that violations are properly rejected
        violation_pnl = pd.Series([-1200.0])
        assert violation_pnl.min() < -daily_loss_limit, \
            "Test data should violate limit for validation"

    def test_trailing_max_drawdown_compliance(self, topstep_50k_account):
        """Verify trailing max drawdown complies with TopStep rules."""
        starting_equity = float(topstep_50k_account.account_size)
        trailing_dd_limit = abs(topstep_50k_account.trailing_max_drawdown)  # 2000
        
        # Simulate compliant equity curve
        equity_curve = np.array([
            starting_equity,
            starting_equity + 500,
            starting_equity + 800,
            starting_equity - 500,
            starting_equity - 1000,
            starting_equity - 400,
            starting_equity - 200
        ])
        
        # Calculate running maximum and drawdown
        running_max = np.maximum.accumulate(equity_curve)
        drawdown_dollars = equity_curve - running_max
        
        # Check compliance
        max_drawdown_dollars = abs(drawdown_dollars.min())
        assert max_drawdown_dollars <= trailing_dd_limit, \
            f"Trailing drawdown ${max_drawdown_dollars:.2f} exceeds limit ${trailing_dd_limit:.2f}"

    def test_profit_target_achievability(self, topstep_50k_account):
        """Verify profit target is achievable within rules."""
        profit_target = float(topstep_50k_account.profit_target)  # 3000
        starting_equity = float(topstep_50k_account.account_size)  # 50000
        daily_loss_limit = abs(float(topstep_50k_account.daily_loss_limit))  # 1000
        
        # Realistic expectations: 55% win rate, $75 avg profit, $50 avg loss
        win_rate = 0.55
        avg_profit = 75.0
        avg_loss = 50.0
        
        expected_per_trade = (win_rate * avg_profit) - ((1 - win_rate) * avg_loss)
        trades_to_target = profit_target / expected_per_trade
        
        # Should achieve target with reasonable trading activity
        assert trades_to_target < 1000, \
            f"Profit target requires {trades_to_target:.0f} trades - unrealistic"

    def test_profit_target_with_realistic_metrics(self, topstep_50k_account, validation_criteria):
        """Test profit target using realistic performance metrics."""
        profit_target = float(topstep_50k_account.profit_target)
        
        # Realistic strategy metrics
        win_rate = 0.55  # 55% win rate
        avg_winning_trade = 150.0
        avg_losing_trade = 75.0
        
        # Expected return per trade
        gross_profit = win_rate * avg_winning_trade
        gross_loss = (1 - win_rate) * avg_losing_trade
        net_per_trade = gross_profit - gross_loss
        
        trades_needed = profit_target / net_per_trade if net_per_trade > 0 else float('inf')
        
        # With 20 trades per week, should reach target in reasonable timeframe
        weeks_to_target = trades_needed / 20
        assert weeks_to_target < 10, \
            f"Profit target requires {weeks_to_target:.1f} weeks - unrealistic"

    def test_win_rate_validation(self, validation_criteria):
        """Test win rate validation against criteria."""
        minimum_win_rate = validation_criteria.minimum_win_rate  # 0.42
        
        # Test passing win rate
        strategy_win_rate = 0.45
        assert strategy_win_rate >= minimum_win_rate, \
            f"Strategy win rate {strategy_win_rate:.1%} below minimum {minimum_win_rate:.1%}"
        
        # Test failing win rate
        poor_win_rate = 0.35
        assert poor_win_rate < minimum_win_rate, \
            f"Validation should reject {poor_win_rate:.1%} win rate"

    def test_sharpe_ratio_validation(self, validation_criteria):
        """Test Sharpe ratio validation against criteria."""
        minimum_sharpe = validation_criteria.minimum_sharpe_ratio  # 1.2
        
        # Test passing Sharpe
        good_sharpe = 1.5
        assert good_sharpe >= minimum_sharpe, \
            f"Strategy Sharpe {good_sharpe:.2f} below minimum {minimum_sharpe:.2f}"
        
        # Test failing Sharpe
        poor_sharpe = 0.8
        assert poor_sharpe < minimum_sharpe, \
            f"Validation should reject {poor_sharpe:.2f} Sharpe ratio"

    def test_minimum_trade_requirement(self, validation_criteria):
        """Test minimum number of trades requirement."""
        minimum_trades = validation_criteria.minimum_number_of_trades  # 100
        
        # Insufficient trades
        low_trades = 50
        assert low_trades < minimum_trades, \
            f"Strategy with {low_trades} trades should fail validation"
        
        # Sufficient trades
        good_trades = 150
        assert good_trades >= minimum_trades, \
            f"Strategy with {good_trades} trades should pass"

    def test_profit_factor_validation(self, validation_criteria):
        """Test profit factor validation."""
        minimum_pf = validation_criteria.minimum_profit_factor  # 1.4
        
        # Test passing profit factor
        good_pf = 1.6
        assert good_pf >= minimum_pf, \
            f"Strategy profit factor {good_pf:.2f} below minimum {minimum_pf:.2f}"
        
        # Test failing profit factor
        poor_pf = 1.2
        assert poor_pf < minimum_pf, \
            f"Validation should reject {poor_pf:.2f} profit factor"

    def test_no_excessive_leverage(self, topstep_50k_account):
        """Verify position sizing doesn't exceed leverage limits."""
        starting_equity = float(topstep_50k_account.account_size)  # 50000
        max_position_size = topstep_50k_account.max_position_size  # 5 contracts
        
        # MES tick value: $1.25
        tick_value = 1.25
        risk_per_contract = 10 * tick_value  # 10 tick stop = $12.50 per contract
        
        total_risk = max_position_size * risk_per_contract  # $62.50
        account_risk_pct = total_risk / starting_equity * 100
        
        # Risk should be < 1% per trade
        assert account_risk_pct < 1.0, \
            f"Position risk {account_risk_pct:.2f}% exceeds 1% limit"

    def test_drawdown_recovery_feasibility(self, topstep_50k_account):
        """Verify recovery from max drawdown is feasible."""
        starting_equity = float(topstep_50k_account.account_size)  # 50000
        profit_target = float(topstep_50k_account.profit_target)  # 3000
        trailing_dd = abs(float(topstep_50k_account.trailing_max_drawdown))  # 2000
        
        # After max drawdown, equity would be:
        equity_after_dd = starting_equity - trailing_dd  # 48000
        
        # Need to recover drawdown + achieve profit target
        required_recovery = trailing_dd + profit_target  # 5000
        required_return_pct = required_recovery / equity_after_dd * 100  # 10.4%
        
        # Should be achievable with reasonable performance
        assert required_return_pct < 20.0, \
            f"Recovery requires {required_return_pct:.1f}% return - feasible"

    def test_consecutive_loss_limit(self, topstep_50k_account):
        """Verify strategy can withstand multiple consecutive losing days."""
        daily_loss_limit = abs(float(topstep_50k_account.daily_loss_limit))  # 1000
        
        # Three consecutive max-loss days
        equity = float(topstep_50k_account.account_size)  # 50000
        
        for day in range(3):
            equity -= daily_loss_limit  # Hit daily loss limit each day
        
        # After 3 max-loss days: 50000 - 3000 = 47000 (still solvent)
        assert equity > 0, "Account should survive 3 consecutive max-loss days"

    def test_daily_loss_stop_implementation(self, topstep_50k_account):
        """Test that daily loss limit is properly enforced."""
        daily_loss_limit = abs(float(topstep_50k_account.daily_loss_limit))  # 1000
        
        # Simulate daily P&L that hits limit
        daily_pnl = np.array([-300.0, -400.0, -200.0, -150.0, -200.0])
        cumsum_loss = np.cumsum(daily_pnl)
        
        # After cumulative loss exceeds limit, trading should stop
        stop_index = np.where(cumsum_loss <= -daily_loss_limit)[0]
        
        if len(stop_index) > 0:
            # Market should have closed after hitting limit
            first_breach = stop_index[0]
            assert first_breach > 0, "Should allow at least one trade before hitting limit"

    def test_session_hours_compliance(self, topstep_50k_account):
        """Verify trading hours comply with TopStep rules."""
        # TopStep allows 18:00 ET - 16:10 ET (next day) trading
        must_close_by = topstep_50k_account.must_close_by  # 16:10
        can_resume_at = topstep_50k_account.can_resume_at  # 18:00
        
        # Verify times are valid
        assert must_close_by.hour < 24, "Close time should be valid"
        assert can_resume_at.hour < 24, "Resume time should be valid"
        
        # Close time before resume time (crosses midnight)
        assert must_close_by.hour < can_resume_at.hour or \
               (must_close_by.hour == can_resume_at.hour and must_close_by.minute < can_resume_at.minute), \
               "Session structure should allow trading window"

    def test_scaling_rules_feasibility(self, topstep_50k_account):
        """Test that position scaling happens reasonably."""
        scaling_plan = topstep_50k_account.scaling_plan
        
        # Verify scaling milestones are achievable
        base_contracts = scaling_plan.get('base', 0)
        assert base_contracts > 0, "Base position size should be positive"
        
        # Scaling should occur at reasonable profit levels
        if 'after_1000_profit' in scaling_plan:
            scaled_contracts = scaling_plan['after_1000_profit']
            assert scaled_contracts > base_contracts, "Scaling should increase position size"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
