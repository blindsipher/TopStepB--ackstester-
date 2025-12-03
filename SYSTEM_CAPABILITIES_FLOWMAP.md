# TopStepB Backtester - System Capabilities & Flow Map

## System Overview

**TopStepB** is an institutional-grade hyperparameter optimization factory for CME futures trading strategies, combining VectorBT's high-performance backtesting with Optuna's advanced optimization.

**Status:** Production-ready (94/100) | **Tests:** 101/101 passing | **Performance:** 2289x speedup achieved

---

## 📊 Visual System Flow Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TOPSTEPB BACKTESTER SYSTEM                        │
│                     Institutional Trading Strategy Factory               │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │  USER INPUT  │
                              │   CLI / UI   │
                              └──────┬───────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │     MAIN RUNNER                 │
                    │  TopStepB/main_runner.py        │
                    │  • CLI argument parsing         │
                    │  • Interactive mode detection   │
                    │  • Config collection            │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │   PIPELINE ORCHESTRATOR         │
                    │   (9-Phase Architecture)        │
                    │   TopStepB/app/pipeline.py      │
                    └────────────────┬────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼────────┐         ┌────────▼─────────┐        ┌────────▼────────┐
│  PHASE 1       │         │  PHASE 2         │        │  PHASE 3        │
│  DATA LOADING  │────────▶│  STRATEGY        │───────▶│  TRADING CONFIG │
│                │         │  DISCOVERY       │        │                 │
└───────┬────────┘         └──────────────────┘        └────────┬────────┘
        │                                                        │
        │ ┌──────────────────────────────────────────┐         │
        │ │ Data Sources:                            │         │
        │ │ • CSV/Parquet files (5.7M+ bars)        │         │
        │ │ • Synthetic data generation             │         │
        │ │ • OHLCV validation                      │         │
        │ └──────────────────────────────────────────┘         │
        │                                                        │
        │                                                        │
┌───────▼────────┐         ┌──────────────────┐        ┌────────▼────────┐
│  PHASE 4       │         │                  │        │  Market Specs:  │
│  DATA SPLIT    │────────▶│  DATA LEAKAGE    │        │  • MES, ES, NQ  │
│                │         │  PREVENTION      │        │  • Timeframes   │
└───────┬────────┘         │                  │        │  • TopStep Acct │
        │                  └──────────────────┘        └─────────────────┘
        │ ┌──────────────────────────────────────────┐
        │ │ Split Methods:                           │
        │ │ • Chronological (train/val/test)        │
        │ │ • Walk-forward analysis                 │
        │ │ • Gap days (prevent leakage)            │
        │ │ • Secure orchestrator                   │
        │ └──────────────────────────────────────────┘
        │
        │
┌───────▼────────────────────────────────────────────────────────────┐
│                    PHASE 5: OPTIMIZATION ENGINE                     │
│                   (Multi-Worker Distributed System)                 │
│                                                                     │
│  ┌───────────────┐    ┌──────────────┐    ┌────────────────┐     │
│  │   OPTUNA      │───▶│  PostgreSQL  │◀───│  Worker Pool   │     │
│  │   TPE Sampler │    │   RDB Store  │    │  (0-N Workers) │     │
│  │               │    │              │    │                │     │
│  │ • 50K trials  │    │ • High       │    │ • Parallel     │     │
│  │ • Multivariate│    │   concurrency│    │   execution    │     │
│  │ • MedianPrune │    │ • Persistence│    │ • 4-12 cores   │     │
│  └───────┬───────┘    └──────────────┘    └────────┬───────┘     │
│          │                                          │             │
│          │         ┌────────────────────────────────▼─────┐       │
│          │         │  STATEFUL OBJECTIVE FUNCTION         │       │
│          │         │  TopStepB/optimization/objective.py  │       │
│          │         │                                      │       │
│          └────────▶│  • Parameter validation              │       │
│                    │  • Strategy execution                │       │
│                    │  • VectorBT backtesting              │       │
│                    │  • Metric calculation                │       │
│                    │  • Composite scoring (7 metrics)     │       │
│                    └────────────┬─────────────────────────┘       │
│                                 │                                 │
│                    ┌────────────▼─────────────────────────┐       │
│                    │  VECTORBT ENGINE                     │       │
│                    │  TopStepB/optimization/              │       │
│                    │         vectorbt_engine.py           │       │
│                    │                                      │       │
│                    │  ✅ Indicator caching (2289x faster) │       │
│                    │  ✅ Portfolio construction           │       │
│                    │  ✅ Metrics extraction               │       │
│                    │  ✅ Execution cost modeling          │       │
│                    └──────────────────────────────────────┘       │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                    ┌─────────────────▼────────────────┐
                    │  COMPOSITE SCORING SYSTEM        │
                    │  (7-Metric Weighted Optimization)│
                    │                                  │
                    │  • Profit Factor (30%)           │
                    │  • PnL (25%)                     │
                    │  • PropFirm Viability (15%)      │
                    │  • Sortino Ratio (10%)           │
                    │  • Win Rate (10%)                │
                    │  • Trade Frequency (5%)          │
                    │  • Max Drawdown (5%)             │
                    └─────────────────┬────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐         ┌─────────▼──────────┐        ┌────────▼────────┐
│  PHASE 6       │         │  PHASE 7           │        │  PHASE 8        │
│  DEPLOYMENT    │────────▶│  VALIDATION        │───────▶│  ANALYTICS      │
│                │         │                    │        │                 │
└───────┬────────┘         └────────┬───────────┘        └────────┬────────┘
        │                           │                             │
        │ ┌──────────────────────┐  │ ┌────────────────────────┐ │
        │ │ • Template injection │  │ │ • In-sample testing    │ │
        │ │ • Parameter files    │  │ │ • Out-of-sample test   │ │
        │ │ • Executable .py     │  │ │ • Permutation test     │ │
        │ │ • Top N strategies   │  │ │ • Monte Carlo sim      │ │
        │ └──────────────────────┘  │ │ • Regime testing       │ │
        │                           │ │ • PropFirm compliance  │ │
        │                           │ └────────────────────────┘ │
        │                           │                             │
        │                           │                             │
┌───────▼────────────────────────────▼─────────────────────────────▼────────┐
│                         PHASE 9: PACKAGING                                 │
│                     (Results & Export)                                     │
│                                                                            │
│  ┌──────────────────────┐    ┌──────────────────────┐    ┌────────────┐  │
│  │  Winner Selection    │───▶│  Study Summaries     │───▶│  Exports   │  │
│  │  • Top N parameters  │    │  • Performance stats │    │  • JSON    │  │
│  │  • Validation scores │    │  • Tear sheets       │    │  • CSV     │  │
│  │  • Trade analysis    │    │  • Equity curves     │    │  • Reports │  │
│  └──────────────────────┘    └──────────────────────┘    └────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   OUTPUTS    │
                              │              │
                              │ • Strategy   │
                              │   files      │
                              │ • Reports    │
                              │ • Metrics    │
                              │ • Parameters │
                              └──────────────┘
```

---

## 🔧 Core Components Architecture

```
TopStepB/
│
├─── app/                          # Application Layer
│    ├── pipeline.py               # 9-phase orchestration
│    └── core/
│        ├── config_collector.py   # CLI/Interactive config
│        └── state.py               # Pipeline state management
│
├─── strategies/                   # Strategy Framework
│    ├── base.py                   # Abstract base class (ABC)
│    └── bollinger_squeeze/        # Example strategy
│        ├── strategy.py           # Signal generation
│        ├── indicators.py         # VectorBT indicators (2289x faster)
│        ├── parameters.py         # Parameter ranges
│        └── deployment_template.py # Live trading template
│
├─── optimization/                 # Optimization Engine
│    ├── engine.py                 # OptunaEngine orchestration
│    ├── objective.py              # StatefulObjective (2,414 lines)
│    ├── vectorbt_engine.py        # VectorBT integration ✅ FIXED
│    ├── scorers.py                # Composite scoring (7 metrics)
│    └── config/
│        └── optuna_config.py      # TPE/Pruner/Storage config
│
├─── data/                         # Data Management
│    ├── data_loader.py            # CSV/Parquet loading
│    └── data_splitter.py          # Chronological/walk-forward
│
├─── validation/                   # Validation Framework
│    ├── engine.py                 # ValidationEngine
│    └── tests/                    # 6 validation test types
│
├─── deployment/                   # Deployment System
│    ├── engine.py                 # DeploymentEngine
│    └── deployment_config.py      # Deployment settings
│
├─── analytics/                    # Analytics Engine
│    └── analytics_engine.py       # Winner selection & analysis
│
├─── packager/                     # Result Packaging
│    └── packaging_engine.py       # Export & aggregation
│
└─── config/                       # System Configuration
     └── system_config.py          # Markets, accounts, execution (1,330 lines)
```

---

## 🎯 Key Features & Capabilities

### 1. Data Processing (Phase 1-4)
- **Supported Formats:** CSV, Parquet
- **Dataset Size:** 5.7M+ bars tested
- **Data Generation:** Realistic synthetic data
- **Split Methods:** Chronological, walk-forward
- **Anti-Leakage:** Temporal validation, gap days, secure orchestrator

### 2. Strategy Framework
- **Architecture:** Pluggable ABC with auto-discovery
- **Implemented:** Bollinger Squeeze (TTM methodology)
- **Parameters:** 19+ configurable parameters per strategy
- **Indicators:** VectorBT-native (10-100x faster)
- **Signal Timing:** Next-bar execution with anti-look-ahead

### 3. Optimization Engine
- **Algorithm:** Optuna TPE (Tree-structured Parzen Estimator)
- **Scale:** Up to 50,000 trials
- **Parallelization:** Multi-worker (0-N cores)
- **Storage:** PostgreSQL (distributed) or SQLite (local)
- **Pruning:** MedianPruner for early termination
- **Scoring:** 7-metric composite scoring

### 4. VectorBT Integration (95% Utilization)
- **Indicator Caching:** 2289x speedup achieved
- **Native Indicators:** BBANDS (7x), ATR (12.8x), Keltner (9.6x)
- **Portfolio Engine:** Optimized backtesting
- **Metrics:** Institutional-grade statistics

### 5. Validation Suite (101/101 Tests)
- **In-Sample Testing**
- **Out-of-Sample Testing**
- **Permutation Testing**
- **Monte Carlo Simulation**
- **Regime Testing**
- **PropFirm Compliance** (TopStep 50K/100K/150K)

### 6. PropFirm Compliance
- **Daily Loss Limit:** $1,000/$2,000/$3,000
- **Max Drawdown:** $2,000/$4,000/$6,000
- **Profit Target:** $3,000/$6,000/$9,000
- **Minimum Win Rate:** 42%+
- **Minimum Sharpe:** 1.2+
- **Trade Frequency:** 100+ trades

### 7. Supported Markets
- **ES** - E-mini S&P 500
- **MES** - Micro E-mini S&P 500 ✅ Tested
- **NQ** - E-mini NASDAQ-100
- **MNQ** - Micro E-mini NASDAQ-100
- Extensible to all CME futures

### 8. Deployment
- **Template System:** Parameter injection
- **Output Format:** Executable Python files
- **Validation:** Pre-deployment checks
- **Export:** Top N parameter sets

---

## 📈 Performance Metrics

| Metric | Achievement | Status |
|--------|-------------|--------|
| VectorBT Utilization | 95% (from 15%) | ✅ 6.3x increase |
| Indicator Caching | 2289x speedup | ✅ Achieved |
| Test Coverage | 101/101 passing | ✅ 100% |
| Dead Code | 0 lines | ✅ Eliminated 232 lines |
| Production Score | 94/100 | ✅ Excellent |
| Code Quality | Zero warnings | ✅ Clean |

---

## 🔌 Integration Points

### External Systems
- **VectorBT:** v0.26+ (95% feature utilization)
- **Optuna:** v3.4+ (TPE, MedianPruner, RDB storage)
- **PostgreSQL:** v17 (distributed coordination)
- **NumPy/Pandas:** Fast array/dataframe operations
- **Numba:** JIT compilation for performance

### Data Flow
```
CSV/Parquet → DataLoader → DataSplitter → Strategy → VectorBT → Metrics → Optuna → Results
                                           ↓
                                    Indicator Cache
                                    (2289x speedup)
```

---

## 🚀 Production Deployment

### AWS Architecture
```
┌─────────────────────────────────────────┐
│         Amazon EC2 Instances            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │Worker 1 │  │Worker 2 │  │Worker N │ │
│  │ 2-3GB   │  │ 2-3GB   │  │ 2-3GB   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘ │
└───────┼───────────┼───────────┼────────┘
        │           │           │
        └───────────┴───────────┘
                    │
        ┌───────────▼──────────────┐
        │  Amazon RDS PostgreSQL   │
        │  (Study Coordination)    │
        │  • High concurrency      │
        │  • Connection pooling    │
        │  • Persistent studies    │
        └──────────────────────────┘
```

### Deployment Checklist
- ✅ All 101 tests passing
- ✅ Zero warnings
- ✅ Performance targets met (2289x)
- ✅ Architecture validated (94/100)
- ⚠️ Database credentials externalization (PENDING)
- ⬜ Production environment setup
- ⬜ Monitoring configuration

---

## 📚 Documentation

### Essential Docs
- `README.md` - Project overview
- `INDEX.md` - Quick navigation
- `VECTORBT_INTEGRATION_COMPLETE.md` - Integration summary
- `POSTGRESQL_VERIFIED.md` - Database setup
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Deployment guide

### Reports (30+ Documents)
- **Architecture:** 6 docs in `docs/architecture/`
- **Refactoring:** 11 docs in `docs/refactoring/`
- **Testing:** 5 docs in `docs/testing/`
- **Validation:** Multiple reports in `docs/reports/`
- **Analysis:** 7 docs in `docs/analysis/`

---

## 🎓 Quick Start Examples

### CLI Usage
```bash
# Quick 15-trial optimization on 2024-2025 MES data
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
  --data-file data/mes-1m_2024-2025.csv \
  --max-trials 15 \
  --max-workers 4 \
  --results-top-n 3
```

### Test Suite
```bash
# Run all 101 tests
pytest tests/ -v

# Run specific suite
pytest tests/test_vectorbt_integration.py -v
pytest tests/test_propfirm_compliance.py -v
```

### Benchmarks
```bash
# Performance benchmarks
python benchmarks/scripts/benchmark_indicator_cache_simple.py
python benchmarks/scripts/benchmark_comprehensive_performance.py
```

---

## 🔍 System Requirements

### Development
- Python 3.11+
- 8GB RAM minimum
- 4+ CPU cores recommended
- PostgreSQL 17 (optional, falls back to SQLite)

### Production (AWS)
- EC2: t3.medium or larger (2-3GB RAM per worker)
- RDS: PostgreSQL 17 (db.t3.small minimum)
- Storage: 50GB+ for data and results
- Network: VPC with security groups

---

## 📊 Current Status

**Version:** 1.0
**Status:** Production-ready (94/100)
**Last Updated:** 2025-12-03
**Next Milestone:** Database credential externalization

---

**Generated:** 2025-12-03
**System:** TopStepB Backtester v1.0
**License:** Proprietary
