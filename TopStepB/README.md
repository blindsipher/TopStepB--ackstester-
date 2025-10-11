# TOPSTEPB - Institutional CME Futures Trading System

Status: Stable, production-oriented. All 7 phases implemented.
Version: 4.0 - Full 7-Phase Pipeline with backtest-to-live timing alignment
Author: blindsipher

## Program Overview

TopStepB is a modular trading research pipeline for CME futures. It orchestrates data loading, strategy discovery, trading configuration, temporal data splitting, parameter optimization with Optuna, validation, analytics, and deployment. The system is CPU-first with optional PostgreSQL study storage and falls back to SQLite when a database is unavailable.

Key capabilities
- Clean data access with anti-leakage controls
- Pluggable strategy architecture (example: TTM Bollinger Squeeze)
- Optuna optimization engine with composite scoring
- Validation and analytics outputs suitable for review
- Deployment packaging for strategy templates

## PostgreSQL Requirement and Configuration

To run distributed optimization (multiple workers or machines), use a PostgreSQL server. For development, a local instance works; for cloud, use a managed service or an EC2-hosted PostgreSQL.

Configure connection in this file:
- `TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/optimization/config/optuna_config.py` (class `StorageConfig`)

Update these fields:
- `host`, `port`, `database`, `username`, `password`

The engine composes the URL as:
```
postgresql://<username>:<password>@<host>:<port>/<database>
```

If PostgreSQL is unreachable, the optimization engine falls back to a local SQLite database under the run results directory.

## Quick Run (CLI)

From this folder:

```
python main_runner.py \
  --strategy bollinger_squeeze \
  --symbol NQ \
  --timeframe 5m \
  --account-type topstep_50k \
  --slippage 1 \
  --commission 4 \
  --contracts-per-trade 1 \
  --split-type walk_forward \
  --synthetic-bars 10000 \
  --max-trials 20 \
  --results-top-n 10 \
  --max-workers 2
```

Outputs
- Tear sheets: `tear_sheets/`
- Deployed strategies: `%USERPROFILE%/.topstep_engine/strategy_packages/deployed_strategies/`
- Logs/results: `%USERPROFILE%/.topstep_engine/{logs,results}/...`

## Current Implementation Status

7-Phase Institutional Pipeline

```
[COMPLETE]  ->  [COMPLETE]  ->  [COMPLETE]  ->  [COMPLETE]  ->  [COMPLETE]  ->  [COMPLETE]  ->  [COMPLETE]
  DATA            STRATEGY        OPTIMIZATION     DEPLOYMENT       VALIDATION      ANALYTICS       PACKAGING
```

Implemented Phases (7/7)

- Phase 1: Data Management (data/)
  - PipelineOrchestrator enforcement; CSV/Parquet loading; robust validation; synthetic generation
- Phase 2: Strategy Discovery (strategies/)
  - BaseStrategy framework; Bollinger Squeeze implementation; stateful execution; parameter ranges and validation
- Phase 3: Optimization (optimization/)
  - Optuna TPE with MedianPruner; PostgreSQL storage with SQLite fallback; composite scoring; parallel workers
- Phase 4: Deployment (deployment/)
  - Parameter injection; template validation; production-ready output with pending-signal timing
- Phase 5: Validation (validation/)
  - In-sample, out-of-sample, permutation, Monte Carlo, noise injection, and regime tests; single-call runner
- Phase 6: Analytics (analytics/)
  - Tear sheet generation with core and pro metrics; cumulative return and drawdown images; frequency handling
- Phase 7: Packaging (packager/)
  - Result aggregation and packaging helpers for downstream consumption

## System Notes

- Database storage: Configured in `optimization/config/optuna_config.py` (PostgreSQL recommended; SQLite fallback automatic)
- Paths with spaces on Windows: wrap the folder path in quotes when invoking scripts
- Parquet: requires `pyarrow` installed

## Development Protocol (condensed)

1) Run a small synthetic job after changes (e.g., 20–100 trials)
2) Review logs for errors and performance regressions
3) Keep change notes and keep tests green

Example checks

```
python main_runner.py --strategy bollinger_squeeze --symbol ES --timeframe 20m \
  --account-type topstep_50k --slippage 0.25 --commission 2.0 --contracts-per-trade 1 \
  --split-type chronological --max-trials 50

python main_runner.py --strategy bollinger_squeeze --symbol ES --timeframe 20m \
  --account-type topstep_50k --slippage 0.25 --commission 2.0 --contracts-per-trade 1 \
  --split-type walk_forward --max-trials 50
```

## Project Structure (high level)

```
TOPSTEPB/
├── main_runner.py                # CLI entry point
├── app/                          # Pipeline and core orchestration
│   ├── pipeline.py
│   └── core/
├── data/                         # Phase 1: Data management
├── strategies/                   # Phase 2: Strategy discovery
├── optimization/                 # Phase 3: Optimization engine
├── deployment/                   # Phase 4: Strategy deployment
├── validation/                   # Phase 5: Validation
├── analytics/                    # Phase 6: Analytics
├── packager/                     # Phase 7: Packaging
├── config/                       # System configuration
├── utils/                        # Shared utilities
├── tests/                        # Test suite
└── docs/                         # Documentation
```

## Change Log (summary)

Version 4.0
- Full 7-phase pipeline implemented end-to-end
- Backtest-to-live execution timing alignment complete
- Analytics and packaging integrated with validation and optimization results

Version 3.x
- PipelineOrchestrator safeguards; composite scoring and optimization engine
- Deployment engine and parameter template injection
- Consistency fixes for indicators and exit logic
