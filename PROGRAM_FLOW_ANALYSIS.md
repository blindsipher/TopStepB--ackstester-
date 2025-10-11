# TopStepB Program Flow & Architecture
Version: 4.0 – Production Ready
Updated: 2025-10-11
Status: All 7 phases implemented and operational
Author: blindsipher

---

## Executive Summary

TopStepB is an institutional-grade trading research and optimization pipeline for CME futures. It implements a complete 7‑phase architecture with secure data handling, composite scoring, and deployment‑ready outputs. The program maintains strict backtest‑to‑live execution consistency and supports distributed optimization via PostgreSQL (with automatic SQLite fallback).

Highlights
- 7/7 phases complete: Data, Strategy, Optimization, Deployment, Validation, Analytics, Packaging
- Anti‑leakage PipelineOrchestrator with AuthorizedDataAccess controls
- Optuna engine with TPE + MedianPruner and composite 7‑metric scoring
- Validation suite with out‑of‑sample and robustness tests
- Analytics tear sheets and packaging for downstream integration

---

## System Architecture Overview

7‑Phase Pipeline
```
[DATA] -> [STRATEGY] -> [OPTIMIZATION] -> [DEPLOYMENT] -> [VALIDATION] -> [ANALYTICS] -> [PACKAGING]
  COMPLETE    COMPLETE       COMPLETE         COMPLETE         COMPLETE        COMPLETE        COMPLETE
```

Implementation Status: 7/7 phases operational

---

## Phase‑by‑Phase Program Flow

### Phase 1: Data Management (COMPLETE)
Location: data/

Flow
1. Entry: main_runner.py -> collect_cli_config() or collect_interactive_config()
2. Data Loading: data_loader.load_data_from_file() or synthetic via create_test_data()
3. Validation: data_validator integrity checks
4. Splitting: create_data_splits() (chronological or walk‑forward with gap days)
5. Security: PipelineOrchestrator.load_data_splits() returns AuthorizedDataAccess objects

Key Components
- DataSplit with immutable train/validation/test
- Temporal ordering and gap enforcement to prevent leakage
- AuthorizedDataAccess per module/phase

### Phase 2: Strategy Discovery (COMPLETE)
Location: strategies/

Flow
1. Discovery: strategies.discover_strategies()
2. Instantiate selected strategy (e.g., Bollinger Squeeze)
3. Validate parameter ranges and constraints
4. Run vectorized signal generation and stateful position management

Consistency Details
- Pending‑signal execution matches deployment template timing
- Unified indicator calculations (rolling std for Bollinger Bands)
- Correct stop‑loss and exit‑method priority rules

### Phase 3: Parameter Optimization (COMPLETE)
Location: optimization/

Flow
1. Engine: OptunaEngine(OptimizationConfig())
2. Storage: PostgreSQL RDBStorage (with connection pooling); fallback to SQLite
3. Objective: StatefulObjective for reduced overhead and parallel safety
4. Execution: Multi‑worker optimization (n_jobs), pruner callbacks, checkpoints
5. Scoring: Composite 7‑metric scoring (PropFirm Viability, Sortino, PNL, MaxDD, Profit Factor, Win Rate, Trade Frequency)
6. Output: Top‑N parameter sets for deployment

### Phase 4: Deployment (COMPLETE)
Location: deployment/

Flow
1. Prepare: Collect top parameter sets
2. Inject: parameter_injector applies parameters into strategy templates
3. Validate: template_validator checks structure and integrity
4. Output: Deployment‑ready strategy files

### Phase 5: Validation (COMPLETE)
Location: validation/

Flow
1. Configure: ValidationConfig and ValidationTestConfig
2. Run: ValidationEngine.run(params) executes selected tests
3. Tests: in‑sample, out‑of‑sample, permutation (in/out), Monte Carlo, noise injection, regime testing
4. Score: Summaries and pass/fail signals aggregated per parameter set

### Phase 6: Analytics (COMPLETE)
Location: analytics/

Flow
1. Metrics: Compute core and professional metrics (with QuantStats when available)
2. Plots: Cumulative return and drawdown images (Matplotlib Agg)
3. Tear Sheets: HTML summaries for in‑sample and out‑of‑sample

### Phase 7: Packaging (COMPLETE)
Location: packager/

Flow
1. Aggregate: Collect optimization/validation results
2. Package: Produce compact outputs for downstream systems

---

## Data Security and Access Controls

- Optimization runs access train/validation only; test data is withheld until validation
- AuthorizedDataAccess ensures module‑scoped permissions
- PipelineOrchestrator keeps an audit trail of access patterns

---

## Performance and Concurrency

- StatefulObjective reduces serialization overhead for parallel trials
- PostgreSQL storage enables high‑concurrency studies; connection pooling is configurable
- Resource monitoring via psutil; safe fallbacks to single‑threaded mode when appropriate

---

## Technology Stack

Core Dependencies
- Python 3.11+
- pandas, numpy
- optuna
- psycopg2‑binary (PostgreSQL)
- matplotlib (Agg backend)
- quantstats (optional)

Architecture Patterns
- Orchestrator (data access control)
- Factory (objective creation)
- Template Method (strategy base)
- Observer (state transitions)

---

## PostgreSQL Configuration

Edit storage settings in optimization/config/optuna_config.py (class StorageConfig).
- host, port, database, username, password
- Engine URL: postgresql://<user>:<pass>@<host>:<port>/<db>

If PostgreSQL is unavailable, the engine automatically falls back to SQLite in the run results directory.

---

## Current Status and Next Steps

Status: Complete 7/7 phases. Stable and production‑oriented.

Next Steps
- Routine maintenance and monitoring
- Strategy library expansion
- Optional: performance tuning for specific instances and datasets

---

This document reflects the current, completed state of the system based on comprehensive code review and testing. All references to incomplete phases have been updated to match the implementation.
