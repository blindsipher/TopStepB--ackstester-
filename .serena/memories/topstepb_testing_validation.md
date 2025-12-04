# TopStepB Testing and Validation

## Test Suite Structure

**Directory**: `tests/`

### Core Integration Tests
- `test_integration_simple.py` - Basic pipeline integration
- `test_full_optuna_optimization.py` - End-to-end optimization flow
- `test_optuna_engine_flow.py` - OptunaEngine execution
- `test_optuna_engine_validation.py` - OptunaEngine validation
- `test_real_strategy.py` - Real strategy execution

### VectorBT Integration Tests
- `test_vectorbt_integration.py` - VectorBT portfolio engine
- `test_vectorbt_scorers_integration.py` - VectorBT + scorers
- `test_indicator_correctness.py` - Indicator cache validation
- `test_signal_parity.py` - Signal generation parity

### Validation System Tests
- `test_validation_engine.py` - ValidationEngine core tests
- `test_validation_analytics_packaging.py` - Full validation->analytics->packaging flow
- `test_data_leakage.py` - Data leakage detection
- `test_walk_forward_integrity.py` - Walk-forward split integrity

### Component Tests
- `test_objective_factory.py` - ObjectiveFactory creation
- `test_error_handling.py` - Error handling flows
- `test_propfirm_compliance.py` - TopStep compliance scoring
- `test_regression_detection.py` - Regression detection
- `test_price_seed_resolver.py` - Price seed resolution
- `test_timezone_utils.py` - Timezone handling

### UI Tests
- `tests/ui/` - UI component tests
- `test_ui_imports.py` - UI import validation

## ValidationEngine Test Framework

**File**: `TopStepB/validation/engine.py`

**Class**: `ValidationEngine`

### Core Test Types

**Always-On Core Tests** (mandatory):
```python
CORE_TESTS = {
    "in_sample",                    # In-sample performance
    "out_of_sample",                # Out-of-sample (test data)
    "in_sample_permutation",        # In-sample permutation test
    "out_of_sample_permutation"     # OOS permutation test
}
```

**Optional Tests** (user-configurable):
- `noise_injection` - Inject noise into returns
- `regime_testing` - Test across market regimes
- Additional custom tests

### Test Configuration

**File**: `TopStepB/validation/config.py`

```python
@dataclass
class ValidationConfig:
    # Core tests (always enabled)
    in_sample: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=True))
    out_of_sample: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=True))
    in_sample_permutation: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=True))
    out_of_sample_permutation: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=True))
    
    # Optional tests
    noise_injection: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=False))
    regime_testing: ValidationTestConfig = field(default_factory=lambda: ValidationTestConfig(enabled=False))
    
    # Minimum trade baselines
    min_trades_in_sample: int = 30
    min_trades_out_of_sample: int = 10
```

### Test Execution Flow

**File**: `TopStepB/validation/engine.py`

```python
def run(self, parameter_sets: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Detect mode: parameter dicts vs deployed files
    if 'file_path' in params_list[0]:
        return self._run_deployed_files(params_list)
    else:
        # Legacy parameter-dict mode
        with ThreadPoolExecutor(max_workers=self.max_workers) as exe:
            return list(exe.map(self._run_single, params_list))
```

### Deployed File Validation

**Method**: `_run_deployed_files(deployed_files)`

**Data Access** (via PipelineOrchestrator):
```python
# In-sample = train + validation
analytics_access = self.orchestrator.get_authorized_data("analytics", phase="analytics")
train_df = analytics_access.train_data
val_df = analytics_access.validation_data

# Out-of-sample = test data
validation_access = self.orchestrator.get_authorized_data("validation", phase="validation")
test_df = validation_access.test_data
```

**ScriptRunner Execution**:
```python
runner = ScriptRunner(
    trading_config=self.trading_config,
    execution_config=self.execution_config,
    loader_mode="importlib"  # Import deployed .py files
)

# Run in-sample (train + validation)
ins = runner.run_in_sample(script_path, train_df, val_df)
in_sample_returns = ins.get("returns", [])
in_sample_trades = ins.get("trade_count", 0)

# Run out-of-sample (test)
oos = runner.run_out_of_sample(script_path, test_df)
out_of_sample_returns = oos.get("returns", [])
out_of_sample_trades = oos.get("trade_count", 0)
```

**Metrics Computation**:
```python
from .metrics import compute_core, compute_overall

# Core metrics (Sortino, Sharpe, max_drawdown)
metrics_in = compute_core(in_sample_returns)
metrics_oos = compute_core(out_of_sample_returns)

# Overall metrics (cumulative stats)
metrics_in_overall = compute_overall(in_sample_returns, equity_base)
metrics_oos_overall = compute_overall(out_of_sample_returns, equity_base)
```

**Test Execution**:
```python
# Run validation tests on enhanced parameter set
enhanced = {
    **item,
    "in_sample_returns": in_sample_returns,
    "out_of_sample_returns": out_of_sample_returns,
    "in_sample_trade_count": in_sample_trades,
    "out_of_sample_trade_count": out_of_sample_trades,
    "metrics": {
        "in": metrics_in,
        "oos": metrics_oos,
        "in_overall": metrics_in_overall,
        "oos_overall": metrics_oos_overall
    }
}

run_res = self._run_single(enhanced)
```

**Minimum Trades Baseline**:
```python
min_in = self.config.min_trades_in_sample  # 30
min_oos = self.config.min_trades_out_of_sample  # 10
baseline_ok = (in_sample_trades >= min_in) and (out_of_sample_trades >= min_oos)

if not baseline_ok:
    # Inject min_trades_baseline test failure
    tests_map["min_trades_baseline"] = {
        "metric": {...},
        "passed": False
    }
    run_res["passed"] = False
```

### Test Result Structure

```python
{
    "params": {...},                    # Parameter set or deployed file info
    "score": 85.3,                      # Total validation score
    "tests": ["in_sample", "out_of_sample", ...],  # Executed tests
    "results": {
        "in_sample": {
            "metric": 42.1,
            "passed": True
        },
        "out_of_sample": {
            "metric": 38.7,
            "passed": True
        },
        "in_sample_permutation": {
            "metric": 0.023,  # p-value
            "passed": True
        },
        "out_of_sample_permutation": {
            "metric": 0.031,
            "passed": True
        }
    },
    "passed": True,                     # All tests passed
    "in_sample_returns": [...],
    "out_of_sample_returns": [...],
    "metrics": {
        "in": {...},                    # In-sample metrics
        "oos": {...},                   # Out-of-sample metrics
        "in_overall": {...},            # In-sample cumulative
        "oos_overall": {...}            # OOS cumulative
    }
}
```

## Test Functions

**File**: `TopStepB/validation/tests/__init__.py`

```python
TEST_FUNCTIONS = {
    "in_sample": test_in_sample,
    "out_of_sample": test_out_of_sample,
    "in_sample_permutation": test_in_sample_permutation,
    "out_of_sample_permutation": test_out_of_sample_permutation,
    "noise_injection": test_noise_injection,
    "regime_testing": test_regime_testing
}
```

**Test Function Signature**:
```python
def test_in_sample(params: Dict[str, Any], rng: np.random.Generator, **kwargs) -> Tuple[float, bool]:
    # Extract in-sample returns
    returns = params.get("in_sample_returns", [])
    
    # Compute metric
    metric = compute_sharpe_ratio(returns)
    
    # Pass/fail threshold
    passed = metric > 1.0
    
    return metric, passed
```

## VectorBT Test Integration

**Test**: `test_vectorbt_integration.py`

**Validates**:
- VectorBT portfolio creation
- Futures P&L calculation (tick-based)
- Commission/slippage handling
- Metric extraction via VectorBTValidator
- IndicatorCache functionality

**Test**: `test_indicator_correctness.py`

**Validates**:
- Indicator cache hit rates
- Cached vs fresh computation equivalence
- Memory usage tracking
- Cache statistics

## Data Leakage Detection

**Test**: `test_data_leakage.py`

**Validates**:
- Test data withheld during optimization
- AuthorizedDataAccess enforcement
- Temporal ordering (train < validation < test)
- No overlap between splits

**Test**: `test_walk_forward_integrity.py`

**Validates**:
- Walk-forward split ordering
- No future data in past windows
- Gap days enforced between splits