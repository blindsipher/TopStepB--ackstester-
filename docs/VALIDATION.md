# TopStepB Validation Framework

**Goal:** Ensure strategies generalize to unseen data and meet institutional standards.

---

## Overview

TopStepB validation framework consists of:
1. **7 validation tests** - Robustness and generalization checks
2. **PropFirm compliance** - TopStep rule enforcement
3. **Out-of-sample testing** - Never seen during optimization
4. **Metrics computation** - 20+ institutional metrics

**Phase in pipeline:** Phase 7 (after deployment, before analytics)

---

## Validation Tests

### Core Tests (Always Enabled)

#### 1. In-Sample Validation
**Purpose:** Baseline performance on training + validation data
**Data:** Train + validation splits (seen during optimization)
**Pass criteria:** Meets minimum performance thresholds

```python
# Metrics computed:
- Total return
- Sharpe ratio ≥ 1.2
- Sortino ratio
- Max drawdown
- Win rate ≥ 50%
- Profit factor ≥ 1.2
- Total trades ≥ 100
```

**Expected:** Best performance (overfitting may occur)

#### 2. Out-of-Sample Validation
**Purpose:** True generalization test
**Data:** Test split (NEVER seen during optimization)
**Pass criteria:** Performance degradation < 30% vs in-sample

**CRITICAL:** This is the ultimate test of strategy viability.

```python
# Acceptance criteria:
out_of_sample_return ≥ (in_sample_return × 0.7)
out_of_sample_sharpe ≥ 1.0
out_of_sample_profit_factor ≥ 1.1
```

**Expected:** 20-40% performance degradation is normal.

---

### Robustness Tests (Optional)

#### 3. In-Sample Permutation Test
**Purpose:** Detect overfitting via label shuffling
**Method:** Shuffle entry/exit labels, recompute metrics

```python
# Process:
1. Take original signals: [1, 0, -1, 0, 1, -1]
2. Shuffle: [0, -1, 1, 0, 1, -1]
3. Run backtest with shuffled signals
4. Compare metrics

# Pass criteria:
original_sharpe >> permuted_sharpe
original_return >> permuted_return
# If permuted performs similarly → overfitting
```

**Interpretation:**
- Permuted Sharpe < 0.5 → Strategy has genuine edge
- Permuted Sharpe ≈ Original → Overfitted (random luck)

#### 4. Out-of-Sample Permutation Test
**Purpose:** Verify robustness on test data
**Method:** Same as in-sample, but on test split

```python
# Pass criteria:
out_of_sample_sharpe >> permuted_sharpe
out_of_sample_profit_factor >> permuted_profit_factor
```

#### 5. Monte Carlo Simulation
**Purpose:** Differentiate from random entries
**Method:** Generate random entry signals, compare performance

```python
# Process:
1. Generate random signals: np.random.choice([-1, 0, 1], size=len(data))
2. Run backtest with random signals (1000 iterations)
3. Compute distribution of returns

# Pass criteria:
strategy_return > 95th_percentile_of_random_returns
# Strategy must beat 95% of random strategies
```

**Interpretation:**
- Strategy in top 5% of random → Real edge
- Strategy ≈ Random → No edge (luck)

#### 6. Regime Testing
**Purpose:** Performance across different market conditions
**Method:** Subsample data by volatility/trend regime

```python
# Regimes:
- Low volatility (VIX < 15)
- Medium volatility (15 ≤ VIX < 25)
- High volatility (VIX ≥ 25)

- Uptrend (price > 200-day MA)
- Downtrend (price < 200-day MA)
- Sideways (near MA)

# Pass criteria:
positive_return_in ≥ 4_out_of_6_regimes
sharpe ≥ 0.8_in_worst_regime
```

**Interpretation:** Strategy should work across multiple market conditions.

#### 7. Noise Injection Test
**Purpose:** Sensitivity to data quality
**Method:** Add Gaussian noise to prices, recompute metrics

```python
# Process:
1. Original close: [100, 101, 102]
2. Add noise (σ=0.1%): [100.05, 100.95, 102.10]
3. Run backtest on noisy data
4. Compare metrics

# Pass criteria:
noisy_sharpe ≥ 0.8 × original_sharpe
noisy_profit_factor ≥ 0.9 × original_profit_factor
# Strategy robust to minor data errors
```

---

## ValidationEngine Architecture

**File:** `TopStepB/validation/engine.py`

### Flow Diagram

```
ValidationEngine.run(deployed_files)
  ↓
1. Get authorized data from PipelineOrchestrator:
   - in_sample: train + validation
   - out_of_sample: test data
  ↓
2. For each deployed strategy file:
   ├─ ScriptRunner.run_in_sample(script_path, train_df, val_df)
   │  └─ Load strategy class
   │  └─ Generate signals on train + validation
   │  └─ Run VectorBT backtest
   │  └─ Extract returns
   │
   ├─ ScriptRunner.run_out_of_sample(script_path, test_df)
   │  └─ Generate signals on test data
   │  └─ Run VectorBT backtest
   │  └─ Extract returns
   │
   └─ Run selected validation tests
  ↓
3. Compute metrics for each test:
   - compute_core(): Sharpe, Sortino, max DD, win rate
   - compute_overall(): Total return, profit factor, trade stats
  ↓
4. Check PropFirm compliance
  ↓
5. Return validation results with pass/fail status
```

### ScriptRunner

**File:** `TopStepB/validation/runner.py`

```python
class ScriptRunner:
    """Execute deployed strategy files bar-by-bar."""

    def run_in_sample(self, script_path, train_df, val_df):
        """Execute strategy on train + validation data."""
        # Load deployed strategy class
        strategy = load_strategy_from_file(script_path)

        # Process each bar
        for _, row in combined_df.iterrows():
            result = strategy.process_new_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume'], str(row.name)
            )
            positions.append(result['position'])

        # Run VectorBT backtest
        portfolio = vbt.Portfolio.from_signals(
            close=combined_df['open'],
            entries=(positions == 1),
            exits=(positions == 0),
            short_entries=(positions == -1)
        )

        return portfolio.returns()

    def run_out_of_sample(self, script_path, test_df):
        """Execute strategy on test data (never seen during optimization)."""
        # Same process as in_sample, but on test data only
        pass
```

**Key feature:** Bar-by-bar execution matches live trading exactly.

---

## Metrics Computation

**File:** `TopStepB/validation/metrics.py`

### Core Metrics
```python
def compute_core(returns):
    """Compute core risk-adjusted metrics."""
    return {
        'sharpe_ratio': empyrical.sharpe_ratio(returns),
        'sortino_ratio': empyrical.sortino_ratio(returns),
        'calmar_ratio': empyrical.calmar_ratio(returns),
        'max_drawdown': empyrical.max_drawdown(returns),
        'max_drawdown_duration': max_dd_duration(returns),
        'volatility': returns.std() * np.sqrt(252),
        'downside_deviation': downside_deviation(returns)
    }
```

### Overall Metrics
```python
def compute_overall(returns, trades):
    """Compute overall performance metrics."""
    return {
        'total_return': (returns + 1).prod() - 1,
        'annual_return': empyrical.annual_return(returns),
        'total_trades': len(trades),
        'win_rate': len(trades[trades > 0]) / len(trades),
        'profit_factor': trades[trades > 0].sum() / abs(trades[trades < 0].sum()),
        'average_trade': trades.mean(),
        'average_win': trades[trades > 0].mean(),
        'average_loss': trades[trades < 0].mean(),
        'largest_win': trades.max(),
        'largest_loss': trades.min(),
        'consecutive_wins': max_consecutive(trades > 0),
        'consecutive_losses': max_consecutive(trades < 0)
    }
```

---

## PropFirm Compliance

**File:** `TopStepB/config/system_config.py`

### TopStep Rules

#### 50K Account
```python
TOPSTEP_50K = AccountConfig(
    starting_capital=50000.0,
    daily_loss_limit=1000.0,      # $1,000 max daily loss
    max_drawdown=2000.0,           # $2,000 max drawdown
    profit_target=3000.0           # $3,000 profit to pass
)
```

**Checks:**
- ✅ No single day loses > $1,000
- ✅ Peak-to-trough never exceeds $2,000
- ✅ Reaches $3,000 profit target
- ✅ Minimum 100 trades (statistical significance)

#### 100K Account
```python
TOPSTEP_100K = AccountConfig(
    starting_capital=100000.0,
    daily_loss_limit=2000.0,      # $2,000 max daily loss
    max_drawdown=4000.0,           # $4,000 max drawdown
    profit_target=6000.0           # $6,000 profit to pass
)
```

#### 150K Account
```python
TOPSTEP_150K = AccountConfig(
    starting_capital=150000.0,
    daily_loss_limit=3000.0,      # $3,000 max daily loss
    max_drawdown=6000.0,           # $6,000 max drawdown
    profit_target=9000.0           # $9,000 profit to pass
)
```

### Compliance Computation

```python
def check_propfirm_compliance(returns, trades, account_config):
    """Verify strategy meets PropFirm rules."""

    # Daily P&L
    daily_pnl = returns.resample('D').sum()
    daily_loss_violations = (daily_pnl < -account_config.daily_loss_limit).sum()

    # Max drawdown
    cumulative_returns = (returns + 1).cumprod()
    peak = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - peak) * account_config.starting_capital
    max_dd_violation = (drawdown < -account_config.max_drawdown).any()

    # Profit target
    total_pnl = returns.sum() * account_config.starting_capital
    profit_target_met = total_pnl >= account_config.profit_target

    # Minimum trades
    sufficient_trades = len(trades) >= 100

    # Minimum Sharpe
    sharpe = empyrical.sharpe_ratio(returns)
    sufficient_sharpe = sharpe >= 1.2

    return {
        'compliant': (daily_loss_violations == 0 and
                     not max_dd_violation and
                     profit_target_met and
                     sufficient_trades and
                     sufficient_sharpe),
        'daily_loss_violations': daily_loss_violations,
        'max_dd_violation': max_dd_violation,
        'profit_target_met': profit_target_met,
        'total_trades': len(trades),
        'sharpe_ratio': sharpe
    }
```

---

## Validation Results

### Output Format

```json
{
  "strategy_file": "bollinger_squeeze_001.py",
  "tests": {
    "in_sample": {
      "status": "PASS",
      "metrics": {
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.45,
        "max_drawdown": -0.12,
        "total_return": 0.45,
        "win_rate": 0.62,
        "profit_factor": 1.73,
        "total_trades": 245
      }
    },
    "out_of_sample": {
      "status": "PASS",
      "metrics": {
        "sharpe_ratio": 1.52,
        "sortino_ratio": 2.01,
        "max_drawdown": -0.15,
        "total_return": 0.32,
        "win_rate": 0.58,
        "profit_factor": 1.51,
        "total_trades": 187
      },
      "degradation": {
        "sharpe": 0.82,
        "return": 0.71,
        "profit_factor": 0.87
      }
    },
    "in_sample_permutation": {
      "status": "PASS",
      "original_sharpe": 1.85,
      "permuted_sharpe": 0.12,
      "ratio": 15.4
    },
    "monte_carlo": {
      "status": "PASS",
      "strategy_return": 0.45,
      "random_mean": 0.02,
      "random_95th_percentile": 0.18,
      "percentile_rank": 99.2
    }
  },
  "propfirm_compliance": {
    "compliant": true,
    "daily_loss_violations": 0,
    "max_dd_violation": false,
    "profit_target_met": true,
    "total_trades": 245,
    "sharpe_ratio": 1.85
  },
  "overall_status": "PASS"
}
```

### Pass/Fail Criteria

**PASS if:**
- ✅ Out-of-sample Sharpe ≥ 1.0
- ✅ Out-of-sample profit factor ≥ 1.1
- ✅ Out-of-sample degradation < 40%
- ✅ Permutation test: Original >> Permuted
- ✅ Monte Carlo: Strategy beats 95th percentile
- ✅ PropFirm compliance: All rules met
- ✅ Minimum 100 trades

**FAIL if any:**
- ❌ Out-of-sample Sharpe < 1.0
- ❌ Out-of-sample profit factor < 1.1
- ❌ Daily loss limit violated
- ❌ Max drawdown exceeded
- ❌ Profit target not met
- ❌ < 100 trades
- ❌ Permuted ≈ Original (overfitting)
- ❌ Strategy ≈ Random (no edge)

---

## Running Validation

### Via Pipeline (Automatic)

```bash
# Validation runs automatically in Phase 7
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol MES \
  --timeframe 1m \
  --account-type topstep_50k \
  --max-trials 100 \
  --validation-tests in_sample,out_of_sample,monte_carlo
```

### Standalone Validation

```python
from validation.engine import ValidationEngine
from validation.config import ValidationConfig

# Configure
config = ValidationConfig()
config.enabled_tests = ['in_sample', 'out_of_sample', 'monte_carlo']

# Run
engine = ValidationEngine(
    config=config,
    orchestrator=secure_orchestrator,
    trading_config=trading_config
)

results = engine.run(deployed_files)
```

---

## Test Selection Guidelines

### Development (Fast Iteration)

```bash
--validation-tests in_sample,out_of_sample
# Runtime: 1-2 minutes
```

### Production (Comprehensive)

```bash
--validation-tests all
# Runtime: 5-10 minutes
# Includes: in_sample, out_of_sample, permutations, monte_carlo, regime, noise
```

### Overfitting Detection

```bash
--validation-tests in_sample,out_of_sample,in_sample_permutation,out_of_sample_permutation
# Runtime: 2-3 minutes
```

### Robustness Testing

```bash
--validation-tests out_of_sample,monte_carlo,regime_testing,noise_injection
# Runtime: 3-5 minutes
```

---

## Interpreting Results

### Excellent Strategy

```
Out-of-sample Sharpe: 1.8
Out-of-sample profit factor: 1.9
Degradation: 15%
Permutation ratio: 12.0
Monte Carlo rank: 98th percentile
PropFirm: PASS (all rules met)
```

**Characteristics:**
- Strong out-of-sample performance
- Low degradation (< 20%)
- Clearly beats permuted/random
- Meets all PropFirm rules

### Good Strategy (Acceptable)

```
Out-of-sample Sharpe: 1.2
Out-of-sample profit factor: 1.3
Degradation: 30%
Permutation ratio: 6.0
Monte Carlo rank: 92nd percentile
PropFirm: PASS
```

**Characteristics:**
- Adequate out-of-sample performance
- Moderate degradation (20-35%)
- Beats permuted/random
- Meets PropFirm rules

### Mediocre Strategy (Review)

```
Out-of-sample Sharpe: 0.9
Out-of-sample profit factor: 1.15
Degradation: 45%
Permutation ratio: 3.5
Monte Carlo rank: 88th percentile
PropFirm: PASS (barely)
```

**Characteristics:**
- Borderline performance
- High degradation (> 40%)
- Marginal edge over random
- Consider rejecting

### Failed Strategy

```
Out-of-sample Sharpe: 0.5
Out-of-sample profit factor: 0.95
Degradation: 65%
Permutation ratio: 1.2
Monte Carlo rank: 65th percentile
PropFirm: FAIL (daily loss violation)
```

**Characteristics:**
- Poor out-of-sample performance
- Severe degradation (> 50%)
- No edge over random/permuted
- Fails PropFirm rules
- **REJECT**

---

## Common Issues

### High Degradation

**Symptom:** Out-of-sample performance << in-sample

**Causes:**
- Overfitting to training data
- Insufficient training data
- Look-ahead bias in strategy
- Market regime change

**Solutions:**
- Increase training data size
- Simplify strategy (fewer parameters)
- Verify timing protocol (shift(1))
- Run walk-forward analysis

### PropFirm Violations

**Symptom:** Strategy fails daily loss or drawdown limits

**Causes:**
- Aggressive position sizing
- No stop losses
- High leverage
- Insufficient risk management

**Solutions:**
- Reduce contracts per trade
- Add ATR-based stops
- Implement position sizing
- Increase stop distance

### Low Trade Count

**Symptom:** < 100 trades in validation

**Causes:**
- Too selective entry conditions
- Insufficient data
- Long holding periods

**Solutions:**
- Increase data size
- Relax entry conditions
- Shorten timeframe
- Adjust exit logic

---

## Testing System

### Test Files

```
tests/
├── test_validation_engine.py           # ValidationEngine tests
├── test_propfirm_compliance.py         # PropFirm rule tests
├── test_signal_parity.py               # Vectorized vs stateful
├── test_data_leakage.py                # Temporal segregation
├── test_indicator_correctness.py       # VectorBT indicator validation
└── test_walk_forward_integrity.py      # Walk-forward validation
```

### Running Tests

```bash
# All validation tests
pytest tests/test_validation_engine.py -v

# PropFirm compliance tests
pytest tests/test_propfirm_compliance.py -v

# Signal parity (critical)
pytest tests/test_signal_parity.py -v

# Full test suite
pytest tests/ -v
```

### Test Coverage

**Validation module:**
- Engine: 95% coverage
- Runner: 98% coverage
- Metrics: 100% coverage
- PropFirm: 100% coverage

**Overall system:** 101/101 tests passing (100%)

---

## Performance

**Validation timing (per strategy):**
- In-sample: 5-10 seconds
- Out-of-sample: 3-5 seconds
- Permutation test: 3-5 seconds
- Monte Carlo (1000 runs): 10-15 seconds
- Regime testing: 8-12 seconds
- Noise injection: 5-8 seconds

**Total (all tests):** 35-55 seconds per strategy

**For top-10 parameter sets:** 6-9 minutes total validation time

---

## Summary

**Validation ensures:**
1. Strategies generalize to unseen data (out-of-sample)
2. Edge is real, not random (monte_carlo, permutation)
3. PropFirm rules are met (compliance checks)
4. Performance is robust (regime, noise tests)
5. Sufficient statistical confidence (trade count, Sharpe)

**Critical tests:**
- **out_of_sample** - True test of generalization
- **PropFirm compliance** - Real-world viability
- **Permutation** - Overfitting detection

**Recommendation:** Run at least `in_sample,out_of_sample` for every optimization. Run `all` tests for production deployment.

---

**Next Steps:**
- Review validation results in `runs/.../validation_results.json`
- Analyze failed strategies for common patterns
- Iterate on strategy logic to improve robustness
- Deploy only strategies passing all tests

**For architecture details:** See `docs/ARCHITECTURE.md`
**For configuration:** See `docs/CONFIGURATION.md`
