# TopStepB Architecture Overview

## System Overview
Institutional-grade futures trading strategy optimization and validation system for TopStep prop firm compliance.

## Core Components

### 1. Entry Points
- **Main Runner**: `TopStepB/main_runner.py` - CLI entry point
- **Pipeline Orchestrator**: `TopStepB/app/pipeline.py` - Main execution coordinator

### 2. Module Organization

#### Data Layer (`TopStepB/data/`)
- `create_test_data()` - Synthetic data generation
- `load_data_from_file()` - File data loading
- `create_data_splits()` - Chronological/walk-forward splitting
- `split_for_backtest()` - Train/val/test splitting logic

#### Strategy Layer (`TopStepB/strategies/`)
- `BaseStrategy` - Abstract strategy interface
- `discover_strategies()` - Auto-discovery of strategy modules
- Strategy subfolders: `bollinger_squeeze/` with `strategy.py`, `indicators.py`, `parameters.py`

#### Optimization Layer (`TopStepB/optimization/`)
- `engine.py` - OptunaEngine main orchestrator
- `vectorbt_engine.py` - VectorBT portfolio backtesting (10-100x faster)
- `parallel.py` - ParallelOptimizer for multicore execution
- `objective.py` - ObjectiveFactory for trial execution
- `scorers.py` - 7-metric composite scoring system
- `config/optuna_config.py` - TPE sampler, pruner, metric normalization

#### Validation Layer (`TopStepB/validation/`)
- `engine.py` - ValidationEngine runs 4+ core tests
- `runner.py` - ScriptRunner executes deployed strategy files
- `metrics.py` - Compute core/overall metrics
- `tests/` - In-sample/OOS permutation tests, noise injection

#### Deployment Layer (`TopStepB/deployment/`)
- `deployment_engine.py` - DeploymentEngine creates executable files
- `parameter_injector.py` - Injects optimized params into templates
- `template_validator.py` - Validates deployment templates

#### Analytics Layer (`TopStepB/analytics/`)
- `engine.py` - AnalyticsEngine selects top-N parameter sets
- `plots.py` - Visualization generation

#### Packaging Layer (`TopStepB/packager/`)
- Prepares winners for delivery

#### Configuration (`TopStepB/config/`)
- `system_config.py` - TradingConfig, market specs, paths

#### Core (`TopStepB/app/core/`)
- `state.py` - PipelineState management
- `pipeline_orchestrator.py` - Secure data access wrapper (AuthorizedDataAccess)

## 9-Phase Pipeline Flow
1. **Data Loading** - Load/generate OHLCV data
2. **Strategy Discovery** - Auto-discover strategy classes
3. **Trading Config** - Create market specifications
4. **Data Splitting** - Chronological or walk-forward splits
5. **Optimization** - Optuna parameter search (OptunaEngine)
6. **Deployment** - Create executable strategy files (DeploymentEngine)
7. **Validation** - Run tests on deployed files (ValidationEngine)
8. **Analytics** - Select top-N parameter sets (AnalyticsEngine)
9. **Packaging** - Prepare final deliverables (PackagingEngine)

## Key Design Principles
- **Separation of Concerns**: Data module handles splits, orchestrator handles security
- **Security-First**: Test data never exposed during optimization (AuthorizedDataAccess)
- **Vectorization**: VectorBT for 10-100x performance gains
- **Institutional Compliance**: TopStep rule adherence scoring
- **Scalability**: PostgreSQL + unlimited workers