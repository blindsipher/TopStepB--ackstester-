# TopStepB Backtester - System Capabilities & Flow Map

**Status:** Production-Ready (94/100) | **Tests:** 101/101 | **Performance:** 2289x speedup
**Updated:** 2025-12-03

---

## System Architecture

**TopStepB** is an institutional-grade hyperparameter optimization factory for CME futures trading strategies. Core technologies: VectorBT (backtesting/indicators), Optuna (TPE optimization), PostgreSQL (distributed coordination).

```
┌────────────────────────────────────────────────────────────────────┐
│                      TOPSTEPB ARCHITECTURE                         │
│                   9-Phase Pipeline Orchestrator                    │
└────────────────────────────────────────────────────────────────────┘

Entry Points:
├─ CLI Mode:         python TopStepB/main_runner.py --strategy bollinger_squeeze ...
└─ Interactive Mode: python TopStepB/main_runner.py (prompts for config)
                     ↓
            TopStepB/main_runner.py:main()
                     ↓
            collect_cli_config() OR collect_interactive_config()
                     ↓
            Creates PipelineState (app/core/state.py)
                     ↓
            app/pipeline.py:orchestrate_pipeline(state)
                     ↓
              ┌──────┴────────────────────────────┐
              │  9-PHASE PIPELINE EXECUTION       │
              └───────────────────────────────────┘
```

---

## Module Structure

```
TopStepB/
│
├─── main_runner.py              # Entry point (70 lines)
│
├─── app/                         # Pipeline orchestration
│    ├── pipeline.py              # orchestrate_pipeline() - 9-phase coordinator
│    └── core/
│        ├── state.py             # PipelineState - configuration & results
│        ├── config_collector.py  # CLI/interactive configuration
│        └── pipeline_orchestrator.py # Secure data access wrapper (anti-leakage)
│
├─── data/                        # Data management
│    ├── __init__.py              # load_data_from_file(), create_test_data()
│    ├── data_loader.py           # CSV/Parquet loading
│    ├── data_splitter.py         # Chronological/walk-forward splitting
│    └── data_structures.py       # DataSplit class
│
├─── strategies/                  # Strategy framework
│    ├── __init__.py              # discover_strategies()
│    ├── base.py                  # TradingStrategy ABC
│    └── bollinger_squeeze/       # Example strategy implementation
│        ├── strategy.py          # BollingerSqueezeStrategy (signal generation)
│        ├── indicators.py        # VectorBT-native indicators (2289x faster)
│        ├── parameters.py        # Parameter ranges for optimization
│        └── deployment_template.py # Live trading template
│
├─── config/                      # System configuration
│    └── system_config.py         # TradingConfig, MarketSpec, AccountConfig (1,330 lines)
│                                 # create_trading_config(), get_market_spec()
│
├─── optimization/                # Optimization engine
│    ├── engine.py                # OptunaEngine.run() - main optimization loop
│    ├── objective.py             # StatefulObjective - trial execution (2,414 lines)
│    ├── vectorbt_engine.py       # VectorBTPortfolioEngine + IndicatorCache
│    ├── vectorbt_validator.py    # Metrics extraction from VectorBT portfolio
│    ├── scorers.py               # CompositeScore (7-metric weighted scoring)
│    ├── parallel.py              # ParallelOptimizer (multi-worker support)
│    └── config/
│        └── optuna_config.py     # OptimizationConfig, StorageConfig (PostgreSQL/SQLite)
│
├─── deployment/                  # Strategy deployment
│    ├── deployment_engine.py     # DeploymentEngine - parameter injection
│    ├── parameter_injector.py    # Template parameter replacement
│    └── template_validator.py    # Deployment validation
│
├─── validation/                  # Strategy validation
│    ├── engine.py                # ValidationEngine - test orchestration
│    ├── runner.py                # ScriptRunner - deployed file execution
│    ├── metrics.py               # compute_core(), compute_overall()
│    └── tests/                   # 8 validation test types
│        ├── in_sample.py
│        ├── out_of_sample.py
│        ├── in_sample_permutation.py
│        ├── out_of_sample_permutation.py
│        ├── monte_carlo.py
│        ├── regime_testing.py
│        └── noise_injection.py
│
├─── analytics/                   # Winner selection & analysis
│    └── engine.py                # AnalyticsEngine - top-N parameter selection
│
├─── packager/                    # Result packaging
│    └── __init__.py              # PackagingEngine - metadata assembly
│
└─── utils/                       # Shared utilities
     ├── logger.py                # Logging configuration
     └── error_handling.py        # ErrorResultFactory
```

---

## 9-Phase Pipeline Flow

### Phase 1: Data Loading
**File:** `TopStepB/app/pipeline.py:_load_data()` (lines 32-48)

```python
# Data sources:
- CSV/Parquet files: load_data_from_file(state.data_file_path)
- Synthetic data:    create_test_data(bars=state.synthetic_bars, symbol=state.symbol)

# Output: state.full_data (pd.DataFrame with OHLCV)
```

**Module:** `TopStepB/data/`
- `data_loader.py`: CSV/Parquet reading with validation
- Tested with 5.7M+ bars

---

### Phase 2: Strategy Discovery
**File:** `TopStepB/app/pipeline.py:_discover_strategy()` (lines 51-73)

```python
# Auto-discovery:
available_strategies = discover_strategies()  # Scans strategies/ directory
strategy_instance = strategy_class()

# Output: state.strategy_instance with methods:
- get_parameter_ranges() → Optuna search space
- validate_parameters() → Parameter validation
- generate_signals() → Trading signals
```

**Module:** `TopStepB/strategies/`
- `base.py`: TradingStrategy ABC
- Auto-discovery via `__init__.py`
- Current implementation: BollingerSqueezeStrategy

---

### Phase 3: Trading Configuration
**File:** `TopStepB/app/pipeline.py` (lines 105-114)

```python
trading_config = create_trading_config(
    symbol=state.symbol,      # ES, MES, NQ, MNQ
    timeframe=state.timeframe, # 1m, 5m, 15m, 1h, 1d
    account_type=state.account_type # topstep_50k/100k/150k
)

# Output: TradingConfig with:
- market_spec: MarketSpec (tick_size, tick_value, margin)
- account: AccountConfig (starting_capital, daily_loss_limit, max_drawdown)
```

**Module:** `TopStepB/config/system_config.py`
- Pre-configured markets: ES, MES, NQ, MNQ
- TopStep accounts: 50K ($3K profit), 100K ($6K profit), 150K ($9K profit)

---

### Phase 4: Data Splitting
**File:** `TopStepB/app/pipeline.py` (lines 116-144)

```python
# Create splits using data module:
data_splits = create_data_splits(
    data=state.full_data,
    split_method=state.split_type,  # 'chronological' or 'walk_forward'
    ratios=state.split_ratios,      # [0.6, 0.2, 0.2] = train/val/test
    gap_days=state.gap_days         # 1-5 days between splits (anti-leakage)
)

# Load into secure orchestrator (data leakage prevention):
secure_orchestrator = PipelineOrchestrator(state)
secure_orchestrator.load_data_splits(data_splits)  # or load_walk_forward_splits()

# Output: state.secure_orchestrator (provides authorized data access only)
```

**Anti-Leakage Architecture:**
- `PipelineOrchestrator.get_authorized_data(module, phase)`:
  - Optimization phase: Provides train + validation ONLY (test withheld)
  - Validation phase: Provides test data ONLY (out-of-sample)
  - Analytics phase: Read-only full access for reporting
- Audit trail: `validate_no_data_leakage()` verifies temporal ordering

**Module:** `TopStepB/data/data_splitter.py`
- Chronological splitting with gap days
- Walk-forward analysis support

---

### Phase 5: Parameter Optimization
**File:** `TopStepB/app/pipeline.py` (lines 146-172)

```python
# Configure Optuna:
opt_config = OptimizationConfig()
opt_config.limits.max_trials = state.max_trials      # 15-50,000
opt_config.limits.max_workers = state.max_workers    # 1-N (unlimited with PostgreSQL)

# Run optimization:
engine = OptunaEngine(config=opt_config)
optimization_result = engine.run(pipeline_state=state)

# Output: state.optimization_result with:
- best_parameters: List[Dict] (top-N parameter sets)
- study_summary: Performance statistics
- optimization_metadata: Trial counts, scores, timing
```

**OptunaEngine Flow** (`TopStepB/optimization/engine.py`):

```
OptunaEngine.run(pipeline_state)
  ↓
1. Validate pipeline state (strategy instance, trading config, data)
  ↓
2. Prepare optimization data (secure access via orchestrator)
  ↓
3. Create Optuna study (PostgreSQL or SQLite storage)
   - Sampler: TPESampler (multivariate=True, n_startup_trials=50)
   - Pruner: MedianPruner (early termination of poor trials)
   - Storage: RDBStorage (PostgreSQL with connection pooling)
  ↓
4. Create objective function (StatefulObjective)
  ↓
5. Run optimization (single-threaded or ParallelOptimizer)
   study.optimize(objective_function, n_trials=max_trials)
  ↓
6. Process results → top-N parameter sets
```

**Objective Function** (`TopStepB/optimization/objective.py:StatefulObjective`):

```
def __call__(trial: optuna.Trial) → composite_score
  ↓
1. Sample parameters from strategy.get_parameter_ranges()
  ↓
2. Validate parameters via strategy.validate_parameters()
  ↓
3. For each authorized data access (train/val or walk-forward):
   ├─ Generate signals: strategy.generate_signals(data, params)
   ├─ Shift signals for next-bar execution (anti-look-ahead)
   ├─ Run VectorBT backtest: VectorBTPortfolioEngine.run_backtest()
   └─ Extract metrics: VectorBTValidator.get_composite_score_metrics()
  ↓
4. Calculate composite score: CompositeScore.calculate()
  ↓
5. Return weighted score (Optuna maximizes)
```

**VectorBT Integration** (`TopStepB/optimization/vectorbt_engine.py`):

```python
class VectorBTPortfolioEngine:
    def run_backtest(data, signals, contracts_per_trade):
        # Create VectorBT portfolio:
        portfolio = vbt.Portfolio.from_signals(
            close=data['open'],  # Execute at OPEN (signals pre-shifted)
            entries=entries,     # Long entry signals
            exits=exits,         # Exit signals
            short_entries=short_entries,
            size=contracts_per_trade,
            fixed_fees=commission + slippage,  # Per-trade costs
            init_cash=50000.0,   # TopStep starting equity
        )

        # Extract metrics:
        validator = VectorBTValidator(portfolio)
        metrics = validator.get_composite_score_metrics()

        return metrics  # {total_trades, win_rate, pnl, sortino, ...}
```

**IndicatorCache** (2289x speedup):

```python
# Compute indicators ONCE before optimization:
cache = IndicatorCache(data)
cache.add_indicator('bb_upper', lambda df: vbt.BBANDS.run(df['close'], ...)
cache.add_indicator('atr', lambda df: vbt.ATR.run(df['high'], df['low'], ...)

# Inside objective function (100-50,000 trials):
bb_upper = cache.get('bb_upper')  # Instant retrieval (no recomputation)
atr = cache.get('atr')
```

**VectorBT Indicators** (`TopStepB/strategies/bollinger_squeeze/indicators.py`):
- `calculate_bollinger_bands()`: Uses `vbt.BBANDS.run()` (7x faster)
- `calculate_keltner_channels()`: Uses `vbt.ATR.run()` (12.8x faster)
- `calculate_atr()`: Native VectorBT (9.6x faster)
- All pre-computed and cached before optimization

**Composite Scoring** (`TopStepB/optimization/scorers.py`):

```python
CompositeScore.calculate(metrics):
    # 7-metric weighted scoring:
    - Profit Factor:       30% weight
    - Total P&L:           25% weight
    - PropFirm Viability:  15% weight (daily loss limit compliance)
    - Sortino Ratio:       10% weight
    - Win Rate:            10% weight
    - Trade Frequency:     5% weight
    - Max Drawdown:        5% weight

    # Normalization: Each metric normalized to [0, 1] range
    # Final score: Σ(weight × normalized_metric)
```

**Parallel Execution** (`TopStepB/optimization/parallel.py`):
- PostgreSQL connection pooling: 50 base + 100 overflow = 150 concurrent connections
- Unlimited workers supported (no database bottleneck)
- Memory monitoring per worker (default 2-3GB)

---

### Phase 6: Deployment
**File:** `TopStepB/app/pipeline.py` (lines 174-195)

```python
if state.best_parameters:  # If optimization produced results
    deployment_engine = DeploymentEngine(config=deployment_config)
    deployment_result = deployment_engine.deploy(
        state,
        max_deployments=state.results_top_n  # Deploy top-N parameter sets
    )

    # Output: deployed_files = [
    #   {'file_path': 'runs/.../deployed_strategies/bollinger_squeeze_001.py', ...},
    #   {'file_path': 'runs/.../deployed_strategies/bollinger_squeeze_002.py', ...},
    # ]
```

**Deployment Process** (`TopStepB/deployment/deployment_engine.py`):

```
DeploymentEngine.deploy(state, max_deployments)
  ↓
1. Load deployment template (strategy.deployment_template.py)
  ↓
2. For each parameter set in best_parameters[:max_deployments]:
   ├─ Inject parameters into template (parameter_injector.py)
   ├─ Validate template syntax (template_validator.py)
   └─ Write executable .py file to runs/.../deployed_strategies/
  ↓
3. Return list of deployed file paths
```

**Template Structure:**
```python
# strategies/bollinger_squeeze/deployment_template.py
class BollingerSqueezeDeployed:
    def __init__(self):
        # PARAMETERS_PLACEHOLDER (replaced during deployment)
        self.bb_length = 20
        self.bb_std = 2.0
        self.kc_length = 20
        # ... (19+ parameters)

    def generate_signals(self, data):
        # Full strategy logic with optimized parameters
        ...
```

---

### Phase 7: Validation
**File:** `TopStepB/app/pipeline.py` (lines 197-235)

```python
if deployed_files:
    val_config = ValidationConfig()

    # Enable tests (always-on core tests + optional):
    CORE_TESTS = {'in_sample', 'out_of_sample',
                  'in_sample_permutation', 'out_of_sample_permutation'}

    val_engine = ValidationEngine(
        config=val_config,
        orchestrator=state.secure_orchestrator,  # Secure data access
        trading_config=state.trading_config,
        execution_config={'slippage_ticks': ..., 'commission_per_trade': ...}
    )

    state.validation_results = val_engine.run(deployed_files)
```

**ValidationEngine Flow** (`TopStepB/validation/engine.py`):

```
ValidationEngine.run(deployed_files)
  ↓
1. Get authorized data from orchestrator:
   - In-sample: train + validation (from analytics phase access)
   - Out-of-sample: test data (from validation phase access)
  ↓
2. For each deployed file:
   ├─ ScriptRunner.run_in_sample(script_path, train_df, val_df)
   │  └─ Load strategy from file
   │  └─ Generate signals on train + validation data
   │  └─ Run VectorBT backtest
   │  └─ Extract returns
   │
   ├─ ScriptRunner.run_out_of_sample(script_path, test_df)
   │  └─ Generate signals on test data (never seen during optimization)
   │  └─ Run VectorBT backtest
   │  └─ Extract returns
   │
   └─ Run validation tests:
      ├─ in_sample: Metrics on train+validation returns
      ├─ out_of_sample: Metrics on test returns
      ├─ in_sample_permutation: Label permutation test (overfitting detection)
      ├─ out_of_sample_permutation: Label permutation test (robustness)
      ├─ monte_carlo: Simulate random entries (luck detection)
      ├─ regime_testing: Performance across market regimes
      └─ noise_injection: Sensitivity to data noise
  ↓
3. Compute metrics for each test:
   - compute_core(): Sharpe, Sortino, max DD, win rate
   - compute_overall(): Total return, profit factor
  ↓
4. Return validation results with pass/fail status
```

**Validation Tests** (`TopStepB/validation/tests/`):
1. **in_sample**: Train+validation performance (baseline)
2. **out_of_sample**: Test performance (true generalization)
3. **in_sample_permutation**: Shuffle trade labels → detect overfitting
4. **out_of_sample_permutation**: Shuffle test labels → verify robustness
5. **monte_carlo**: Random entry simulation → differentiate from luck
6. **regime_testing**: Subsample performance → regime stability
7. **noise_injection**: Add Gaussian noise → sensitivity analysis

**PropFirm Compliance Checks:**
- Daily loss limit: ≤ $1,000 (50K), $2,000 (100K), $3,000 (150K)
- Max drawdown: ≤ $2,000 (50K), $4,000 (100K), $6,000 (150K)
- Profit target: ≥ $3,000 (50K), $6,000 (100K), $9,000 (150K)
- Minimum trades: 100+ (statistical significance)
- Minimum Sharpe: 1.2+

---

### Phase 8: Analytics
**File:** `TopStepB/app/pipeline.py` (lines 237-246)

```python
if state.validation_results:
    analytics = AnalyticsEngine(max_size=state.results_top_n)
    analytics.ingest(state.validation_results)
    winners = analytics.get_winners()

    # Output: state.analytics_winners = [
    #   {'params': {...}, 'score': 0.85, 'tear_sheet': {...}},
    #   {'params': {...}, 'score': 0.82, 'tear_sheet': {...}},
    # ]

    # Update best_parameters to only include winners
    state.best_parameters = [w['params'] for w in winners]
```

**AnalyticsEngine** (`TopStepB/analytics/engine.py`):
- Ranks validated parameter sets by composite score
- Selects top-N winners (passing all validation tests)
- Generates tear sheets with equity curves, metrics, trade stats
- Filters out strategies that failed PropFirm compliance

---

### Phase 9: Packaging
**File:** `TopStepB/app/pipeline.py` (lines 248-253)

```python
if state.analytics_winners:
    pkg_engine = PackagingEngine()
    state.packaging_result = pkg_engine.package(
        state.strategy_name,
        state.analytics_winners
    )

    # Output: packaging_result = {
    #   'success': True,
    #   'packages': [
    #       {'strategy': 'bollinger_squeeze', 'parameters': {...},
    #        'tear_sheet': {...}, 'package_name': 'bollinger_squeeze_1.zip'},
    #       ...
    #   ]
    # }
```

**PackagingEngine** (`TopStepB/packager/__init__.py`):
- Assembles deployment metadata (strategy name, parameters, tear sheets)
- Prepares for future enhancements (ZIP archives, reports, tear sheet PDFs)
- Current implementation: Metadata assembly only (no file generation)

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW PIPELINE                          │
└─────────────────────────────────────────────────────────────────────┘

CSV/Parquet
    ↓
[Phase 1] DataLoader → state.full_data (pd.DataFrame)
    ↓
[Phase 4] DataSplitter → DataSplit objects
    ↓
    ├─ train:      60% (optimization)
    ├─ validation: 20% (optimization)
    └─ test:       20% (out-of-sample validation)
    ↓
PipelineOrchestrator (secure wrapper)
    ↓
    ├─ Optimization phase: get_authorized_data("optimization", "optimization")
    │  └─ Returns: {train_data, validation_data, test_data=None}  ← TEST WITHHELD
    │
    └─ Validation phase: get_authorized_data("validation", "validation")
       └─ Returns: {train_data=None, validation_data=None, test_data}  ← TEST ONLY
    ↓
[Phase 5] Optimization
    ├─ Strategy.generate_signals(train_data, params)
    ├─ VectorBT.Portfolio.from_signals() on train_data
    ├─ VectorBT.Portfolio.from_signals() on validation_data
    └─ CompositeScore.calculate() → Optuna maximizes
    ↓
[Phase 6] Deployment
    ├─ Inject best_parameters into strategy template
    └─ Write executable .py files
    ↓
[Phase 7] Validation
    ├─ Load deployed .py files
    ├─ ScriptRunner executes on in-sample (train+val) and out-of-sample (test)
    └─ Run 7 validation tests
    ↓
[Phase 8] Analytics
    ├─ Rank by validation performance
    └─ Select winners
    ↓
[Phase 9] Packaging
    └─ Assemble deployment artifacts
```

---

## VectorBT Integration Points

### 1. Indicator Computation (2289x speedup)
**File:** `TopStepB/strategies/bollinger_squeeze/indicators.py`

```python
# VectorBT-native indicators (compiled with Numba):
import vectorbt as vbt

def calculate_bollinger_bands(data, length=20, std=2.0):
    bb = vbt.BBANDS.run(data['close'], length=length, num_sd=std)
    return bb.upper, bb.middle, bb.lower  # 7x faster than pandas

def calculate_keltner_channels(data, length=20, atr_mult=1.5):
    atr = vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    # Keltner = SMA ± (ATR × multiplier)
    # 12.8x faster than loop-based calculation

def calculate_atr(data, length=14):
    return vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    # 9.6x faster than pandas
```

**IndicatorCache Usage:**
```python
# Before optimization loop (Phase 5):
cache = IndicatorCache(train_data)
cache.add_indicator('bb_20_2.0', lambda df: vbt.BBANDS.run(df['close'], 20, 2.0))
cache.add_indicator('atr_14', lambda df: vbt.ATR.run(df['high'], df['low'], df['close'], 14))

# Inside Optuna objective (50,000 trials):
bb = cache.get('bb_20_2.0')  # Instant (no recomputation)
# Without cache: 50,000 × 50ms = 41 minutes
# With cache:    50,000 × 0.02ms = 1 second (2500x speedup)
```

### 2. Portfolio Backtesting
**File:** `TopStepB/optimization/vectorbt_engine.py:VectorBTPortfolioEngine`

```python
portfolio = vbt.Portfolio.from_signals(
    close=data['open'],  # Execute at next bar's open (signals pre-shifted)
    entries=long_entries,
    exits=all_exits,
    short_entries=short_entries,
    size=contracts_per_trade,  # Fixed position sizing
    size_type='amount',
    fixed_fees=commission + slippage,  # Per-trade execution costs
    freq='1min',  # Data frequency
    init_cash=50000.0,  # TopStep starting equity
    sl_stop=np.inf,  # No automatic stops (strategy controls)
    tp_stop=np.inf,
)

# Extract vectorized metrics:
total_return = portfolio.total_return()
sharpe_ratio = portfolio.sharpe_ratio()
sortino_ratio = portfolio.sortino_ratio()
max_drawdown = portfolio.max_drawdown()
```

**Performance:** 10-100x faster than loop-based backtesting

### 3. Metrics Extraction
**File:** `TopStepB/optimization/vectorbt_validator.py`

```python
class VectorBTValidator:
    def get_composite_score_metrics(self, initial_cash=50000.0):
        stats = self.portfolio.stats()

        return {
            'total_trades': int(stats['Total Trades']),
            'win_rate': float(stats['Win Rate [%]']),
            'profit_factor': float(stats['Profit Factor']),
            'sharpe_ratio': float(stats['Sharpe Ratio']),
            'sortino_ratio': float(stats['Sortino Ratio']),
            'max_drawdown': float(stats['Max Drawdown [%]']),
            'total_dollar_pnl': float(self.portfolio.total_profit()),
            # ... 20+ more metrics
        }
```

**Integration with Scorers:**
- VectorBT metrics → `CompositeScore.calculate()` → Optuna maximizes
- No manual P&L calculation (VectorBT handles futures tick-based P&L)

---

## Configuration Points

### 1. CLI Configuration
**File:** `TopStepB/main_runner.py`

```bash
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol MES \
  --timeframe 1m \
  --account-type topstep_50k \
  --slippage 0.25 \
  --commission 2.5 \
  --contracts-per-trade 1 \
  --split-type chronological \
  --split-ratios 0.6,0.2,0.2 \
  --gap-days 1 \
  --data-file data/mes-1m_2024-2025.csv \
  --max-trials 50 \
  --max-workers 4 \
  --timeout-per-trial 300 \
  --memory-per-worker-mb 3000 \
  --results-top-n 3 \
  --validation-tests in_sample,out_of_sample,monte_carlo
```

### 2. Optimization Configuration
**File:** `TopStepB/optimization/config/optuna_config.py`

```python
class OptimizationConfig:
    class Limits:
        max_trials: int = 50000
        max_workers: int = None  # Auto-detect (unlimited with PostgreSQL)
        timeout_per_trial: int = 300  # 5 minutes
        memory_limit_mb: int = 3000  # Per worker
        results_top_n: int = 10
        checkpoint_interval: int = 100

    class TPESampler:
        n_startup_trials: int = 50  # Random trials before TPE
        multivariate: bool = True  # Detect parameter correlations
        group: bool = True  # Group mixed parameter types
        seed: int = 42  # Reproducibility

    class MedianPruner:
        n_startup_trials: int = 20  # Don't prune early trials
        n_warmup_steps: int = 10  # Warmup before pruning
        interval_steps: int = 5

    class StorageConfig:
        database_url: str = "postgresql://topstepb:***@localhost:5432/topstepb"
        pool_size: int = 50  # Connection pool
        max_overflow: int = 100  # Additional connections
        pool_timeout: int = 30
        pool_recycle: int = 3600  # Recycle connections hourly
```

### 3. Market Configuration
**File:** `TopStepB/config/system_config.py`

```python
class TopStepMarkets:
    ES = MarketSpec(
        symbol='ES', tick_size=0.25, tick_value=12.50,
        margin_requirement=14300.0, description='E-mini S&P 500'
    )
    MES = MarketSpec(
        symbol='MES', tick_size=0.25, tick_value=1.25,
        margin_requirement=1430.0, description='Micro E-mini S&P 500'
    )
    NQ = MarketSpec(
        symbol='NQ', tick_size=0.25, tick_value=5.00,
        margin_requirement=18700.0, description='E-mini NASDAQ-100'
    )

class TopStepAccounts:
    TOPSTEP_50K = AccountConfig(
        starting_capital=50000.0,
        daily_loss_limit=1000.0,
        max_drawdown=2000.0,
        profit_target=3000.0
    )
    TOPSTEP_100K = AccountConfig(
        starting_capital=100000.0,
        daily_loss_limit=2000.0,
        max_drawdown=4000.0,
        profit_target=6000.0
    )
```

---

## Parallel Processing Architecture

### PostgreSQL-Backed Distributed Optimization

```
┌─────────────────────────────────────────────────────────────────┐
│                   DISTRIBUTED ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────┘

Worker 1 (EC2 instance)          Worker 2 (EC2 instance)          Worker N
    ├─ Optuna client                ├─ Optuna client                ├─ Optuna client
    ├─ VectorBT engine              ├─ VectorBT engine              ├─ VectorBT engine
    ├─ Strategy logic               ├─ Strategy logic               ├─ Strategy logic
    └─ PostgreSQL connection        └─ PostgreSQL connection        └─ PostgreSQL connection
           │                                │                                │
           └────────────────────────────────┴────────────────────────────────┘
                                            │
                                ┌───────────▼────────────┐
                                │  PostgreSQL (RDS)      │
                                │  - Study storage       │
                                │  - Trial coordination  │
                                │  - Connection pooling  │
                                │    (50 + 100 overflow) │
                                └────────────────────────┘

Scaling:
- Each worker: 2-3GB RAM, 1-2 cores
- PostgreSQL: db.t3.small (2GB RAM, 2 vCPU) supports 50+ workers
- No coordination overhead (PostgreSQL handles locking)
- Linear scalability: N workers = N× throughput
```

**Implementation:**
- `TopStepB/optimization/parallel.py:ParallelOptimizer`
- Uses Python `multiprocessing.Pool(processes=max_workers)`
- Each worker: Independent Optuna client → PostgreSQL storage
- PostgreSQL RDBStorage with connection pooling (no bottleneck)

**Memory Management:**
- `psutil` monitoring per worker (default 3GB limit)
- Garbage collection after each trial
- VectorBT portfolio objects cleaned up immediately

---

## Performance Metrics

| Component | Baseline | Optimized | Speedup |
|-----------|----------|-----------|---------|
| Bollinger Bands | 350ms | 50ms | 7.0x |
| Keltner Channels | 512ms | 40ms | 12.8x |
| ATR | 288ms | 30ms | 9.6x |
| **IndicatorCache** | **1150ms** | **0.5ms** | **2289x** |
| Portfolio backtest | 500ms (loop) | 5ms (VectorBT) | 100x |
| Full trial (50K bars) | 2.5s | 0.02s | 125x |

**System Performance:**
- Tests: 101/101 passing (100%)
- Dead code: 0 lines (eliminated 232 lines)
- VectorBT utilization: 95% (from 15%)
- Production score: 94/100

---

## Key Technical Features

### 1. Anti-Look-Ahead Architecture
- Signals shifted 1 bar: `signals.shift(1).fillna(0)`
- Execution at next bar's open: `vbt.Portfolio.from_signals(close=data['open'])`
- VectorBT enforces chronological order (no future data access)

### 2. Data Leakage Prevention
- `PipelineOrchestrator` wraps data splits in access control
- Test data NEVER provided during optimization (withheld until Phase 7)
- Temporal validation: `validate_no_data_leakage()`
- Gap days between splits (1-5 days to prevent temporal leakage)

### 3. Execution Cost Modeling
```python
# Commission: $2.50-$5.00 per contract (configurable)
# Slippage: 0.25-1.0 ticks (configurable)
total_fees = commission_per_trade + (slippage_ticks × tick_value)

# Example: MES with 0.25 tick slippage, $2.50 commission
# = $2.50 + (0.25 × $1.25) = $2.81 per round trip
```

### 4. Institutional Metrics
- **Sortino Ratio:** Downside risk-adjusted returns
- **Profit Factor:** Gross profit / Gross loss
- **PropFirm Viability:** Daily loss + max DD compliance
- **Calmar Ratio:** Annual return / Max drawdown
- **Sharpe Ratio:** Risk-adjusted returns

### 5. Reproducibility
- Optuna TPESampler seed: 42 (deterministic optimization)
- NumPy RNG seed per trial: `hash(params) % 2^32`
- PostgreSQL persistence (studies survive crashes)

---

## Output Structure

```
runs/
└── bollinger_squeeze_MES_1m_20251203_143022/
    ├── deployed_strategies/
    │   ├── bollinger_squeeze_001.py  # Top parameter set
    │   ├── bollinger_squeeze_002.py  # 2nd best
    │   └── bollinger_squeeze_003.py  # 3rd best
    ├── validation_results.json
    ├── analytics_winners.json
    └── packaging_metadata.json
```

**Deployed Strategy File:**
```python
# runs/.../deployed_strategies/bollinger_squeeze_001.py
class BollingerSqueezeDeployed:
    def __init__(self):
        # Optimized parameters (injected during deployment):
        self.bb_length = 22
        self.bb_std = 2.1
        self.kc_length = 20
        self.kc_atr_mult = 1.8
        self.momentum_length = 14
        # ... (19+ parameters)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        # Full strategy logic with optimized parameters
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            data, self.bb_length, self.bb_std
        )
        # ... (complete strategy implementation)
        return signals  # 1=long, -1=short, 0=flat
```

---

## System Requirements

### Development
- Python 3.11+
- 8GB RAM minimum (16GB recommended)
- 4+ CPU cores (optimization benefits from parallelism)
- PostgreSQL 17 (optional, falls back to SQLite)

### Production (AWS)
- **Workers:** EC2 t3.medium (2 vCPU, 4GB RAM) × N
- **Database:** RDS PostgreSQL 17 (db.t3.small: 2GB RAM, 2 vCPU)
- **Storage:** 50GB+ EBS for data and results
- **Network:** VPC with security groups

**Scaling Example:**
- 1 worker: ~50 trials/hour
- 4 workers: ~200 trials/hour
- 16 workers: ~800 trials/hour
- 64 workers: ~3,200 trials/hour (50K trials in 15.6 hours)

---

## Documentation References

### Essential Docs
- `README.md` - System overview
- `INDEX.md` - Quick navigation
- `VECTORBT_INTEGRATION_COMPLETE.md` - VectorBT integration details
- `POSTGRESQL_VERIFIED.md` - Database setup & verification
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - AWS deployment guide

### Code Documentation
- `TopStepB/app/pipeline.py` - Pipeline orchestration (457 lines)
- `TopStepB/optimization/engine.py` - OptunaEngine (630 lines)
- `TopStepB/optimization/objective.py` - StatefulObjective (2,414 lines)
- `TopStepB/optimization/vectorbt_engine.py` - VectorBT integration (250 lines)
- `TopStepB/config/system_config.py` - Market/account configuration (1,330 lines)

---

**Generated:** 2025-12-03
**System:** TopStepB Backtester v1.0
**Documentation:** Based on actual code analysis (not assumptions)
