# TOPSTEPB - Cloud Hyperparameter Optimization Factory
TopStepx backtesting Hyperparameter Factory (7/7 phases complete)
Author: blindsipher

## Program Overview and Current State

***its CPU/ ram intenssive so putting it on an aws cluster might help***

TopStepB is a cloud-scalable hyperparameter optimization factory for CME futures strategies. It targets AWS deployment with distributed coordination via PostgreSQL, enabling long-horizon parameter optimization across many workers. The architecture focuses on backtest-to-live consistency, error handling, memory management, and distributed coordination.

Core mission: Deploy to AWS with 2–3GB per worker, optimize strategy parameters across historical data, then export optimized parameters for live trading systems.

---

## Cloud Deployment Architecture

AWS Optimization Strategy
```
Local Development -> AWS Upload -> PostgreSQL Coordination -> Distributed Workers -> Parameter Export
```

Deployment specifications
- Target platform: Amazon EC2 (2–3GB per core)
- Coordination: PostgreSQL backend supporting many concurrent workers
- Optimization scope: 10+ years per strategy
- Performance: Parallelization over local-only optimization

Production-ready cloud features
- Memory management and cleanup
- Error recovery for distributed failures
- PostgreSQL-backed result aggregation
- Template export for live integration
- Stateful objective to reduce overhead

---

## Current Implementation Status

7-Phase Cloud Pipeline (all complete)
```
[COMPLETE] -> [COMPLETE] -> [COMPLETE] -> [COMPLETE] -> [COMPLETE] -> [COMPLETE] -> [COMPLETE]
  DATA         STRATEGY        OPTIMIZATION     DEPLOYMENT        VALIDATION       ANALYTICS        PACKAGING
```

Highlights by phase
- Data Management: anti-leakage controls, CSV/Parquet loading, validation
- Strategy Discovery: pluggable architecture, Bollinger Squeeze example, stateful execution
- Optimization: Optuna TPE, MedianPruner, PostgreSQL storage with SQLite fallback, composite scoring
- Deployment: parameter injection, template validation, pending-signal timing
- Validation: in-sample, out-of-sample, permutation, Monte Carlo, noise injection, regime testing
- Analytics: metrics and tear sheets (cumulative return, drawdown), frequency handling
- Packaging: result aggregation for downstream use

---

## PostgreSQL Requirement and Configuration

To run distributed optimization (multiple workers or multiple machines), you need a PostgreSQL server. A local instance is sufficient for development; for AWS, use a managed instance or a self-hosted EC2 PostgreSQL server.

Where to configure
- Edit the storage settings in:
  `TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/optimization/config/optuna_config.py: StorageConfig`

Fields to update in `StorageConfig`:
- `host`: PostgreSQL host (e.g., localhost or server DNS)
- `port`: PostgreSQL port (e.g., 5432)
- `database`: Database name (e.g., optuna_optimization)
- `username`: Database user
- `password`: Database password

Connection string used by the engine
```
postgresql://<username>:<password>@<host>:<port>/<database>
```

Notes
- If PostgreSQL connection fails, the engine falls back to local SQLite storage under the run results directory.
- For high concurrency, ensure sufficient connection pool size on the PostgreSQL server.

---

## Quick Start

### Option 1: Streamlit UI (Recommended)

**Windows Launch:**
```cmd
scripts\run_ui.bat
```

**Manual Launch:**
```cmd
python -m streamlit run src/ui/app.py
```

**Access:**
- URL: http://localhost:8501
- Auto-opens in default browser

The Streamlit UI provides:
- Visual configuration interface
- File upload and synthetic data generation
- Real-time optimization monitoring
- Interactive results visualization
- Study history and management

See the comprehensive user guide: `docs/UI_USER_GUIDE.md`

### Option 2: Command Line Interface

Example local run
```
python "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/main_runner.py" \
  --strategy bollinger_squeeze --symbol ES --timeframe 20m \
  --max-trials 100 --max-workers 4
```

AWS run (conceptual)
```
tar -czf topstepb-cloud.tar.gz TopStepB/
scp topstepb-cloud.tar.gz user@aws-instance:/opt/
python3 main_runner.py --strategy bollinger_squeeze \
  --symbol ES --timeframe 20m --max-trials 10000 --max-workers 50
```

**Note**: Both UI and CLI can be used interchangeably and share the same PostgreSQL database for results.

---

## Development Environment

Install
```
pip install -r requirements.txt
```

Validate
```
python3 "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/main_runner.py" --strategy bollinger_squeeze --max-trials 10
```

---

## Version History (summary)

4.1 – Streamlit UI Release
- Complete Streamlit-based user interface
- 5-phase UI: Configuration, Data Loading, Monitoring, Results, History
- Real-time optimization monitoring with auto-refresh
- Interactive Plotly visualizations
- Configuration templates and export functionality
- Full CLI backward compatibility

4.0 – Cloud Production Ready
- All 7 phases implemented and tested
- Backtest-to-live execution alignment
- Cloud-oriented performance and memory management

3.x – Consistency and Engine
- Pipeline orchestrator, composite scoring, deployment engine
- Consistency fixes for indicators and exit logic

---

## Documentation

- **User Interface Guide**: `docs/UI_USER_GUIDE.md` - Complete UI usage instructions
- **Program Flow Analysis**: `PROGRAM_FLOW_ANALYSIS.md` - System architecture and flow
- **PostgreSQL Setup**: `README-POSTGRESQL.md` - Database configuration
- **Quick Start**: `README-QUICKSTART.md` - Getting started guide
- **Strategy Development**: `docs/STRATEGY_DEVELOPMENT_GUIDE.md` - Creating new strategies

---

For technical flow details, see `PROGRAM_FLOW_ANALYSIS.md`.
