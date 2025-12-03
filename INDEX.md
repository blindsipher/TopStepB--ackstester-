# TopStepB Backtester - Quick Navigation

## 📋 Start Here

**New Users:**
1. Read `README.md` - Project overview
2. Read `README-QUICKSTART.md` - Get started in 5 minutes
3. Read `claude.md` - AI assistant reference

**System Overview:**
- `VECTORBT_INTEGRATION_COMPLETE.md` - Complete VectorBT integration summary ⭐

**Production Deployment:**
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Pre-deployment checklist
- `README-POSTGRESQL.md` - PostgreSQL setup

---

## 📁 Directory Structure

```
/home/jake/Desktop/TopStepB--ackstester-/
├── TopStepB/                    # Main source code
│   ├── optimization/            # VectorBT + Optuna optimization
│   ├── strategies/              # Trading strategies
│   ├── data/                    # Data handling
│   └── config/                  # Configuration
│
├── tests/                       # 101 comprehensive tests
│   ├── test_vectorbt_integration.py
│   ├── test_regression_detection.py
│   ├── test_indicator_correctness.py
│   ├── test_data_leakage.py
│   └── [7 more test suites]
│
├── data/                        # Market data files
│   └── mes-1m_data.csv         # 5.7M bars MES data
│
├── docs/                        # 📚 All documentation
│   ├── architecture/            # System architecture (6 docs)
│   ├── refactoring/             # Refactoring reports (11 docs)
│   ├── testing/                 # Testing reports (5 docs)
│   ├── validation/              # Validation reports (1 doc)
│   ├── analysis/                # System analysis (7 docs)
│   └── reports/                 # Phase & validation reports
│       ├── phase-completion/    # Phase 1-3 reports
│       └── validation/          # Validation reports
│
├── benchmarks/                  # Performance benchmarks
│   ├── scripts/                 # Benchmark scripts (5 files)
│   └── results/                 # Benchmark results
│
├── scripts/                     # Utility scripts
├── logs/                        # Application logs
└── .github/                     # CI/CD workflows
```

---

## 📚 Documentation Index

### Essential Reading (Start Here)
- `README.md` - Project overview
- `README-QUICKSTART.md` - Quick start guide
- `VECTORBT_INTEGRATION_COMPLETE.md` - Master summary
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Deployment guide

### Architecture & Design
📁 `docs/architecture/`
- `OPTUNA_VECTORBT_ARCHITECTURE_ANALYSIS.md` - Complete architecture
- `DATA_FLOW_DIAGRAM.md` - System flow visualization
- `VECTORBT_INTEGRATION.md` - VectorBT integration details

### Implementation Details
📁 `docs/refactoring/`
- Phase completion reports (Phases 1-3)
- Before/after comparisons
- Implementation summaries

### Testing & Validation
📁 `docs/reports/validation/`
- `CORRECTNESS_VALIDATION_REPORT.md` - 57/57 tests passing
- `PERFORMANCE_VALIDATION_REPORT.md` - Performance benchmarks
- `INTEGRATION_VALIDATION_REPORT.md` - 94/100 production score
- `TEST_INFRASTRUCTURE_REPORT.md` - 101 tests documentation

### Analysis & Research
📁 `docs/analysis/`
- Data flow analysis
- Edge case analysis
- Program flow documentation

---

## 🚀 Quick Commands

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test suite
pytest tests/test_vectorbt_integration.py -v
pytest tests/test_regression_detection.py -v
pytest tests/test_performance_benchmarks.py -v
```

### Run Optimization
```bash
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol MES \
  --timeframe 1m \
  --max-trials 100 \
  --max-workers 4 \
  --data-file data/mes-1m_data.csv
```

### Run Benchmarks
```bash
python benchmarks/scripts/benchmark_indicator_cache_simple.py
python benchmarks/scripts/benchmark_comprehensive_performance.py
```

---

## 🎯 Key Performance Metrics

| Metric | Achievement |
|--------|-------------|
| **VectorBT Utilization** | 95% (from 15%) |
| **Indicator Caching** | 2289x speedup |
| **Test Coverage** | 101/101 passing (100%) |
| **Code Quality** | -232 lines dead code removed |
| **Production Ready** | 94/100 score |

---

## 📞 Support

- **Documentation Issues:** Check `docs/` folder
- **Setup Problems:** Read `README-QUICKSTART.md`
- **Performance Questions:** See `PERFORMANCE_VALIDATION_REPORT.md`
- **Testing Help:** See `TEST_INFRASTRUCTURE_REPORT.md`

---

## 🔄 Recent Updates

**Latest:** VectorBT Integration Complete (Phase 1-5)
- ✅ All 15 agents completed successfully
- ✅ 2289x indicator speedup achieved
- ✅ 101/101 tests passing
- ✅ Production-ready (94/100 score)

**Next:** Production deployment after database password fix

---

**Last Updated:** 2025-12-03
**Version:** 1.0
**Status:** Production Ready
