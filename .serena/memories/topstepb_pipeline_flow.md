# TopStepB Pipeline Execution Flow

## Pipeline Entry Point
**File**: `TopStepB/app/pipeline.py`
**Function**: `orchestrate_pipeline(state: PipelineState)`

## Phase-by-Phase Execution

### Phase 1: Data Loading
**Function**: `_load_data(state)`
**Files**: `TopStepB/data/__init__.py`

```python
if state.data_file_path:
    full_data = load_data_from_file(state.data_file_path)
else:
    full_data = create_test_data(bars=state.synthetic_bars, symbol=state.symbol)
```

**Output**: `state.full_data` (OHLCV DataFrame)

### Phase 2: Strategy Discovery
**Function**: `_discover_strategy(state)`
**Files**: `TopStepB/strategies/__init__.py`

```python
available_strategies = discover_strategies()  # Auto-discovers strategy subfolders
strategy_instance = available_strategies[state.strategy_name]()
state.strategy_instance = strategy_instance
```

**Output**: `state.strategy_instance`, `strategy_result` dict

### Phase 3: Trading Configuration
**Files**: `TopStepB/config/system_config.py`

```python
trading_config = create_trading_config(
    symbol=state.symbol,
    timeframe=state.timeframe,
    account_type=state.account_type
)
state.trading_config = trading_config
```

**Output**: `state.trading_config` (TradingConfig with market specs)

### Phase 4: Data Splitting
**Files**: `TopStepB/data/__init__.py`, `TopStepB/app/core/pipeline_orchestrator.py`

```python
# Data module creates splits
data_splits = create_data_splits(
    data=state.full_data,
    split_method=state.split_type,  # "chronological" or "walk_forward"
    ratios=state.split_ratios,
    gap_days=state.gap_days
)

# Orchestrator loads splits for secure access
secure_orchestrator = PipelineOrchestrator(state)
if state.split_type == "chronological":
    secure_orchestrator.load_data_splits(data_splits)
elif state.split_type == "walk_forward":
    secure_orchestrator.load_walk_forward_splits(data_splits)

state.secure_orchestrator = secure_orchestrator
```

**Output**: `state.secure_orchestrator` (secure data access wrapper)

### Phase 5: Parameter Optimization
**Files**: `TopStepB/optimization/engine.py`, `TopStepB/optimization/objective.py`

```python
from optimization import OptunaEngine
from optimization.config.optuna_config import OptimizationConfig

opt_config = OptimizationConfig()
opt_config.limits.max_trials = state.max_trials
opt_config.limits.max_workers = state.max_workers
engine = OptunaEngine(config=opt_config)

optimization_result = engine.run(pipeline_state=state)
state.best_parameters = optimization_result.get('best_parameters', [])
```

**Execution Flow**:
1. `engine._validate_pipeline_state()` - Check strategy, config, data
2. `engine._prepare_optimization_data()` - Get authorized data from orchestrator
3. `engine._create_optuna_study()` - Create PostgreSQL-backed study
4. `objective_factory.create_objective()` - Create trial objective function
5. `parallel_optimizer.run_parallel_optimization()` - Execute trials with n_jobs workers
6. `engine._process_optimization_results()` - Extract top-N parameter sets

**Data Access**:
```python
# Optimization gets train+validation ONLY (test withheld)
access = orchestrator.get_authorized_data("optimization", phase="optimization")
# access.train_data, access.validation_data available
# access.test_data = None (withheld for security)
```

**Output**: `state.best_parameters` (list of 1-500 parameter dicts), `state.optimization_result`

### Phase 6: Deployment
**Files**: `TopStepB/deployment/deployment_engine.py`

```python
from deployment import DeploymentEngine
deployment_engine = DeploymentEngine(config=deployment_config)
deployment_result = deployment_engine.deploy(state, max_deployments=state.results_top_n)

deployed_files = deployment_result.get('deployed_files', [])
state.deployment_result = deployment_result
```

**Output**: Executable strategy files in `TopStepB/deployed_strategies/`

### Phase 7: Validation
**Files**: `TopStepB/validation/engine.py`, `TopStepB/validation/runner.py`

```python
from validation import ValidationEngine, ValidationConfig

# Core tests: in_sample, out_of_sample, in_sample_permutation, out_of_sample_permutation
val_config = ValidationConfig()
val_engine = ValidationEngine(
    config=val_config,
    orchestrator=state.secure_orchestrator,
    trading_config=state.trading_config,
    execution_config={'slippage_ticks': 0, 'commission_per_trade': 0}
)
state.validation_results = val_engine.run(deployed_files)
```

**Data Access**:
```python
# Validation gets test data for OOS testing
analytics_access = orchestrator.get_authorized_data("analytics", phase="analytics")
validation_access = orchestrator.get_authorized_data("validation", phase="validation")

train_df = analytics_access.train_data
val_df = analytics_access.validation_data
test_df = validation_access.test_data
```

**Output**: `state.validation_results` (list of test results per deployed file)

### Phase 8: Analytics
**Files**: `TopStepB/analytics/engine.py`

```python
from analytics import AnalyticsEngine

analytics = AnalyticsEngine(max_size=state.results_top_n)
analytics.ingest(state.validation_results)
winners = analytics.get_winners()

state.analytics_winners = winners
state.best_parameters = [w['params'] for w in winners]  # Update to winning params only
```

**Output**: `state.analytics_winners` (top-N parameter sets by validation score)

### Phase 9: Packaging
**Files**: `TopStepB/packager/__init__.py`

```python
from packager import PackagingEngine

pkg_engine = PackagingEngine()
state.packaging_result = pkg_engine.package(state.strategy_name, state.analytics_winners)
```

**Output**: `state.packaging_result` (packaged deliverables)

## State Transformations

**Initial State**: `PipelineState(strategy_name, symbol, timeframe, ...)`

**After Phase 1**: `state.full_data` populated

**After Phase 4**: `state.secure_orchestrator` provides controlled data access

**After Phase 5**: `state.best_parameters` (1-500 param sets), `state.optimization_result`

**After Phase 6**: `deployed_files` list with executable strategy paths

**After Phase 7**: `state.validation_results` with test metrics

**After Phase 8**: `state.analytics_winners` (top-N filtered by validation)

**After Phase 9**: `state.packaging_result` ready for delivery

## Final Assembly

```python
result = _create_success_result(state, strategy_result, split_result)
state.prune_heavy_state()  # Memory cleanup
result['pipeline_state'] = state
```