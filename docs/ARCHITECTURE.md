# TopStepB System Architecture

**Status:** Production-Ready (94/100) | **Tests:** 101/101 Passing

---

## System Overview

TopStepB is an institutional-grade hyperparameter optimization factory for CME futures trading strategies.

**Core Technologies:**
- **VectorBT** - Vectorized backtesting (100-2289x speedup)
- **Optuna** - TPE-based hyperparameter optimization
- **PostgreSQL** - Distributed coordination and study storage

**Full details:** See `SYSTEM_CAPABILITIES_FLOWMAP.md` (925 lines)

---

## Architecture Diagram

```
TopStepB/main_runner.py (Entry Point)
         ↓
   collect_cli_config() or collect_interactive_config()
         ↓
   PipelineState (app/core/state.py)
         ↓
   app/pipeline.py:orchestrate_pipeline(state)
         ↓
   ┌─────────────────────────────────────┐
   │  9-PHASE PIPELINE ORCHESTRATION     │
   └─────────────────────────────────────┘
```

---

## Module Structure

```
TopStepB/
│
├── main_runner.py              # Entry point (70 lines)
│
├── app/                         # Pipeline orchestration
│   ├── pipeline.py              # 9-phase coordinator (457 lines)
│   └── core/
│       ├── state.py             # PipelineState - config & results
│       ├── config_collector.py  # CLI/interactive input
│       └── pipeline_orchestrator.py # Data access wrapper (anti-leakage)
│
├── data/                        # Data management
│   ├── data_loader.py           # CSV/Parquet loading
│   ├── data_splitter.py         # Train/val/test splitting
│   └── data_structures.py       # DataSplit class
│
├── strategies/                  # Strategy framework
│   ├── base.py                  # TradingStrategy ABC
│   └── bollinger_squeeze/       # Example strategy
│       ├── strategy.py          # Signal generation
│       ├── indicators.py        # VectorBT indicators (2289x speedup)
│       ├── parameters.py        # Optimization ranges
│       └── deployment_template.py # Live trading template
│
├── config/                      # System configuration
│   └── system_config.py         # TradingConfig, MarketSpec, AccountConfig (1,330 lines)
│
├── optimization/                # Optimization engine
│   ├── engine.py                # OptunaEngine - main loop
│   ├── objective.py             # StatefulObjective - trial execution (2,414 lines)
│   ├── vectorbt_engine.py       # VectorBTPortfolioEngine + IndicatorCache
│   ├── vectorbt_validator.py    # Metrics extraction
│   ├── scorers.py               # CompositeScore (7-metric weighted)
│   ├── parallel.py              # ParallelOptimizer (multi-worker)
│   └── config/optuna_config.py  # OptimizationConfig (PostgreSQL/SQLite)
│
├── deployment/                  # Strategy deployment
│   ├── deployment_engine.py     # DeploymentEngine
│   ├── parameter_injector.py    # Template injection
│   └── template_validator.py    # Deployment validation
│
├── validation/                  # Strategy validation
│   ├── engine.py                # ValidationEngine
│   ├── runner.py                # ScriptRunner - bar-by-bar execution
│   ├── metrics.py               # Metric computation
│   └── tests/                   # 8 validation test types
│       ├── in_sample.py
│       ├── out_of_sample.py
│       ├── in_sample_permutation.py
│       ├── out_of_sample_permutation.py
│       ├── monte_carlo.py
│       ├── regime_testing.py
│       └── noise_injection.py
│
├── analytics/                   # Winner selection
│   └── engine.py                # AnalyticsEngine - top-N selection
│
├── packager/                    # Result packaging
│   └── __init__.py              # PackagingEngine
│
└── utils/                       # Utilities
    ├── logger.py                # Logging
    └── error_handling.py        # Error factories
```

---

## 9-Phase Pipeline Flow

### Phase 1: Data Loading
**File:** `app/pipeline.py:_load_data()` (lines 32-48)

```python
# Sources:
- CSV/Parquet: load_data_from_file(path)
- Synthetic:   create_test_data(bars=10000, symbol='MES')

# Output: state.full_data (pd.DataFrame with OHLCV)
```

**Tested with:** 5.7M+ bars

---

### Phase 2: Strategy Discovery
**File:** `app/pipeline.py:_discover_strategy()` (lines 51-73)

```python
# Auto-discovery via strategies/ directory scan
available_strategies = discover_strategies()
strategy_instance = strategy_class()

# Output: state.strategy_instance with methods:
- get_parameter_ranges() → Optuna search space
- validate_parameters()  → Parameter validation
- generate_signals()     → Trading signals
```

**Current strategies:** BollingerSqueezeStrategy

---

### Phase 3: Trading Configuration
**File:** `app/pipeline.py` (lines 105-114)

```python
trading_config = create_trading_config(
    symbol=state.symbol,      # ES, MES, NQ, MNQ
    timeframe=state.timeframe, # 1m, 5m, 15m, 1h, 1d
    account_type=state.account_type # topstep_50k/100k/150k
)

# Output: TradingConfig with:
- market_spec: MarketSpec (tick_size, tick_value, margin)
- account: AccountConfig (capital, limits, profit target)
```

**Pre-configured markets:** ES, MES, NQ, MNQ
**TopStep accounts:** 50K ($3K profit), 100K ($6K), 150K ($9K)

---

### Phase 4: Data Splitting
**File:** `app/pipeline.py` (lines 116-144)

```python
# Create splits
data_splits = create_data_splits(
    data=state.full_data,
    split_method=state.split_type,  # 'chronological' or 'walk_forward'
    ratios=state.split_ratios,      # [0.6, 0.2, 0.2] = train/val/test
    gap_days=state.gap_days         # 1-5 days anti-leakage gap
)

# Load into secure wrapper (data leakage prevention)
secure_orchestrator = PipelineOrchestrator(state)
secure_orchestrator.load_data_splits(data_splits)
```

**Anti-Leakage Architecture:**
- Optimization phase: Provides train + validation ONLY (test withheld)
- Validation phase: Provides test data ONLY (out-of-sample)
- Analytics phase: Read-only full access for reporting
- Audit trail: `validate_no_data_leakage()` verifies temporal ordering

---

### Phase 5: Optimization
**File:** `app/pipeline.py` (lines 146-172)

```python
# Configure Optuna
opt_config = OptimizationConfig()
opt_config.limits.max_trials = state.max_trials
opt_config.limits.max_workers = state.max_workers

# Run optimization
engine = OptunaEngine(config=opt_config)
optimization_result = engine.run(pipeline_state=state)
```

**OptunaEngine Flow:**

```
OptunaEngine.run()
  ↓
1. Validate pipeline state
  ↓
2. Prepare optimization data (secure access)
  ↓
3. Create Optuna study (PostgreSQL or SQLite)
   - Sampler: TPESampler (multivariate=True, n_startup_trials=50)
   - Pruner: MedianPruner (early termination)
   - Storage: RDBStorage (PostgreSQL with pooling)
  ↓
4. Create objective function (StatefulObjective)
  ↓
5. Run optimization: study.optimize(objective, n_trials=max_trials)
  ↓
6. Process results → top-N parameter sets
```

**Objective Function (StatefulObjective):**

```python
def __call__(trial: optuna.Trial) → composite_score:
  ↓
1. Sample parameters from strategy.get_parameter_ranges()
  ↓
2. Validate parameters via strategy.validate_parameters()
  ↓
3. For each data access (train/val or walk-forward):
   ├─ Generate signals: strategy.generate_signals(data, params)
   ├─ Shift signals for next-bar execution (anti-look-ahead)
   ├─ Run VectorBT backtest: VectorBTPortfolioEngine.run_backtest()
   └─ Extract metrics: VectorBTValidator.get_composite_score_metrics()
  ↓
4. Calculate composite score: CompositeScore.calculate()
  ↓
5. Return weighted score (Optuna maximizes)
```

**VectorBT Integration:**

```python
portfolio = vbt.Portfolio.from_signals(
    close=data['open'],  # Execute at OPEN (signals pre-shifted)
    entries=entries,
    exits=exits,
    short_entries=short_entries,
    size=contracts_per_trade,
    fixed_fees=commission + slippage,
    init_cash=50000.0
)

metrics = VectorBTValidator(portfolio).get_composite_score_metrics()
```

**IndicatorCache (2289x speedup):**

```python
# Compute indicators ONCE before optimization
cache = IndicatorCache(data)
cache.add_indicator('bb_upper', lambda df: vbt.BBANDS.run(df['close'], 20, 2.0))

# Inside objective function (5,000 trials)
bb_upper = cache.get('bb_upper')  # Instant retrieval (no recomputation)
```

**Composite Scoring (7 metrics, weighted):**
- Profit Factor: 30%
- Total P&L: 25%
- PropFirm Viability: 15%
- Sortino Ratio: 10%
- Win Rate: 10%
- Trade Frequency: 5%
- Max Drawdown: 5%

**Parallel Execution:**
- PostgreSQL connection pooling: 50 base + 100 overflow
- Unlimited workers supported
- Memory monitoring per worker (default 2-3GB)

---

### Phase 6: Deployment
**File:** `app/pipeline.py` (lines 174-195)

```python
if state.best_parameters:
    deployment_engine = DeploymentEngine(config=deployment_config)
    deployment_result = deployment_engine.deploy(
        state,
        max_deployments=state.results_top_n  # Top-N parameter sets
    )
```

**Deployment Process:**

```
DeploymentEngine.deploy()
  ↓
1. Load deployment template (strategy.deployment_template.py)
  ↓
2. For each parameter set in best_parameters[:max_deployments]:
   ├─ Inject parameters into template
   ├─ Validate template syntax
   └─ Write executable .py file to runs/.../deployed_strategies/
  ↓
3. Return list of deployed file paths
```

**Template Injection Example:**

```python
# Before injection:
bb_length = {bb_length}
bb_std = {bb_std}

# After injection:
bb_length = 20
bb_std = 2.0
```

---

### Phase 7: Validation
**File:** `app/pipeline.py` (lines 197-235)

```python
if deployed_files:
    val_config = ValidationConfig()
    val_engine = ValidationEngine(
        config=val_config,
        orchestrator=state.secure_orchestrator,
        trading_config=state.trading_config
    )
    state.validation_results = val_engine.run(deployed_files)
```

**ValidationEngine Flow:**

```
ValidationEngine.run(deployed_files)
  ↓
1. Get authorized data:
   - In-sample: train + validation
   - Out-of-sample: test data (never seen during optimization)
  ↓
2. For each deployed file:
   ├─ ScriptRunner.run_in_sample(script_path, train_df, val_df)
   ├─ ScriptRunner.run_out_of_sample(script_path, test_df)
   └─ Run validation tests:
      ├─ in_sample: Metrics on train+validation
      ├─ out_of_sample: Metrics on test (true generalization)
      ├─ in_sample_permutation: Overfitting detection
      ├─ out_of_sample_permutation: Robustness verification
      ├─ monte_carlo: Random entry simulation (luck detection)
      ├─ regime_testing: Performance across market regimes
      └─ noise_injection: Sensitivity to data noise
  ↓
3. Compute metrics (compute_core, compute_overall)
  ↓
4. Return validation results with pass/fail status
```

**PropFirm Compliance Checks:**
- Daily loss limit: ≤ $1K (50K), $2K (100K), $3K (150K)
- Max drawdown: ≤ $2K (50K), $4K (100K), $6K (150K)
- Profit target: ≥ $3K (50K), $6K (100K), $9K (150K)
- Minimum trades: 100+ (statistical significance)
- Minimum Sharpe: 1.2+

---

### Phase 8: Analytics
**File:** `app/pipeline.py` (lines 237-246)

```python
if state.validation_results:
    analytics = AnalyticsEngine(max_size=state.results_top_n)
    analytics.ingest(state.validation_results)
    winners = analytics.get_winners()

    state.analytics_winners = winners
    state.best_parameters = [w['params'] for w in winners]
```

**AnalyticsEngine:**
- Ranks validated parameter sets by composite score
- Selects top-N winners (passing all validation tests)
- Generates tear sheets (equity curves, metrics, trade stats)
- Filters out strategies failing PropFirm compliance

---

### Phase 9: Packaging
**File:** `app/pipeline.py` (lines 248-253)

```python
if state.analytics_winners:
    pkg_engine = PackagingEngine()
    state.packaging_result = pkg_engine.package(
        state.strategy_name,
        state.analytics_winners
    )
```

**PackagingEngine:**
- Assembles deployment metadata (strategy name, parameters, tear sheets)
- Current implementation: Metadata assembly only
- Future: ZIP archives, PDF reports, tear sheet PDFs

---

## Data Flow Architecture

```
CSV/Parquet → [Phase 1] DataLoader → state.full_data
                           ↓
           [Phase 4] DataSplitter → train (60%), validation (20%), test (20%)
                           ↓
               PipelineOrchestrator (secure wrapper)
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓                                      ↓
[Phase 5] Optimization               [Phase 7] Validation
- Train + Validation ONLY            - Test data ONLY
- Test data WITHHELD                 - Out-of-sample
        ↓                                      ↓
[Phase 6] Deployment ← best_parameters → [Phase 8] Analytics
        ↓                                      ↓
    Executable .py files                   Winners ranked
```

---

## VectorBT Integration Points

### 1. Indicator Computation (2289x speedup)

**File:** `strategies/bollinger_squeeze/indicators.py`

```python
import vectorbt as vbt

def calculate_bollinger_bands(data, length=20, std=2.0):
    bb = vbt.BBANDS.run(data['close'], length=length, num_sd=std)
    return bb.upper, bb.middle, bb.lower  # 7x faster than pandas

def calculate_keltner_channels(data, length=20, atr_mult=1.5):
    atr = vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    # 12.8x faster than loop-based

def calculate_atr(data, length=14):
    return vbt.ATR.run(data['high'], data['low'], data['close'], window=length)
    # 9.6x faster than pandas
```

### 2. Portfolio Backtesting (10-100x speedup)

**File:** `optimization/vectorbt_engine.py`

```python
portfolio = vbt.Portfolio.from_signals(
    close=data['open'],  # Execute at next bar's open
    entries=long_entries,
    exits=all_exits,
    short_entries=short_entries,
    size=contracts_per_trade,
    fixed_fees=commission + slippage,
    freq='1min',
    init_cash=50000.0
)

# Extract vectorized metrics
total_return = portfolio.total_return()
sharpe_ratio = portfolio.sharpe_ratio()
sortino_ratio = portfolio.sortino_ratio()
max_drawdown = portfolio.max_drawdown()
```

### 3. Metrics Extraction

**File:** `optimization/vectorbt_validator.py`

```python
class VectorBTValidator:
    def get_composite_score_metrics(self):
        stats = self.portfolio.stats()
        return {
            'total_trades': int(stats['Total Trades']),
            'win_rate': float(stats['Win Rate [%]']),
            'profit_factor': float(stats['Profit Factor']),
            'sharpe_ratio': float(stats['Sharpe Ratio']),
            'sortino_ratio': float(stats['Sortino Ratio']),
            'max_drawdown': float(stats['Max Drawdown [%]']),
            'total_dollar_pnl': float(self.portfolio.total_profit())
        }
```

---

## Performance Metrics

| Component | Baseline | Optimized | Speedup |
|-----------|----------|-----------|---------|
| Bollinger Bands | 350ms | 50ms | 7.0x |
| Keltner Channels | 512ms | 40ms | 12.8x |
| ATR | 288ms | 30ms | 9.6x |
| **IndicatorCache** | **1150ms** | **0.5ms** | **2289x** |
| Portfolio backtest | 500ms | 5ms | 100x |
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
- VectorBT enforces chronological order

### 2. Data Leakage Prevention
- `PipelineOrchestrator` wraps data splits in access control
- Test data NEVER provided during optimization
- Temporal validation: `validate_no_data_leakage()`
- Gap days between splits (1-5 days)

### 3. Execution Cost Modeling
```python
# Commission: $2.50-$5.00 per contract
# Slippage: 0.25-1.0 ticks
total_fees = commission_per_trade + (slippage_ticks × tick_value)

# Example: MES with 0.25 tick slippage, $2.50 commission
# = $2.50 + (0.25 × $1.25) = $2.81 per round trip
```

### 4. Institutional Metrics
- Sortino Ratio (downside risk-adjusted returns)
- Profit Factor (gross profit / gross loss)
- PropFirm Viability (daily loss + max DD compliance)
- Calmar Ratio (annual return / max drawdown)
- Sharpe Ratio (risk-adjusted returns)

### 5. Reproducibility
- Optuna TPESampler seed: 42
- NumPy RNG seed per trial: `hash(params) % 2^32`
- PostgreSQL persistence (studies survive crashes)

---

## Output Structure

```
runs/bollinger_squeeze_MES_1m_20251203_143022/
├── deployed_strategies/
│   ├── bollinger_squeeze_001.py  # Top parameter set
│   ├── bollinger_squeeze_002.py  # 2nd best
│   └── bollinger_squeeze_003.py  # 3rd best
├── validation_results.json
├── analytics_winners.json
└── packaging_metadata.json
```

---

## System Requirements

### Development
- Python 3.11+
- 8GB RAM minimum (16GB recommended)
- 4+ CPU cores
- PostgreSQL 17 (optional, SQLite fallback)

### Production (AWS)
- Workers: EC2 t3.medium (2 vCPU, 4GB RAM) × N
- Database: RDS PostgreSQL 17 (db.t3.small)
- Storage: 50GB+ EBS

**Scaling Example:**
- 1 worker: ~50 trials/hour
- 4 workers: ~200 trials/hour
- 16 workers: ~800 trials/hour
- 64 workers: ~3,200 trials/hour (50K trials in 15.6 hours)

---

## Documentation References

**Essential:**
- `SYSTEM_CAPABILITIES_FLOWMAP.md` - Complete system map (925 lines)
- `docs/QUICKSTART.md` - Run pipeline in 5 minutes
- `docs/STRATEGY_GUIDE.md` - Create strategies
- `docs/CONFIGURATION.md` - Configure system
- `docs/VALIDATION.md` - Testing framework

**Technical:**
- `VECTORBT_INTEGRATION_COMPLETE.md` - VectorBT details
- `POSTGRESQL_VERIFIED.md` - Database setup
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - AWS deployment

---

**Updated:** 2025-12-03
**System:** TopStepB Backtester v1.0
**Documentation:** Based on actual code analysis
