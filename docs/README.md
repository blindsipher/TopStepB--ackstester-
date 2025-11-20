# TopStepB Documentation Index

Complete documentation for the TopStepB backtesting and optimization system.

## Quick Start

- [**Quickstart Guide**](../README-QUICKSTART.md) - Get started in 5 minutes
- [**Main README**](../README.md) - Overview and installation
- [**Strategy Development Guide**](../STRATEGY_GUIDE.md) - Create your own strategies (ROOT)

## Core Documentation

### Strategy Development
- [Strategy Development Guide](STRATEGY_DEVELOPMENT_GUIDE.md) - Complete guide to building strategies
- [Strategy Requirements Specification](STRATEGY_REQUIREMENTS_SPECIFICATION.md) - Technical specifications

### System Architecture
- [Data Flow Analysis](architecture/DATA_FLOW_ANALYSIS_REPORT.md) - How data flows through the system
- [Data Flow Diagram](architecture/DATA_FLOW_DIAGRAM.md) - Visual architecture diagrams
- [Program Flow Analysis](architecture/PROGRAM_FLOW_ANALYSIS.md) - Execution flow documentation

### Performance Optimizations
- [Vectorized Backtest Summary](optimizations/VECTORIZED_BACKTEST_SUMMARY.md) - 4x faster backtesting
- [Combined Optimizations Report](optimizations/COMBINED_OPTIMIZATIONS_REPORT.md) - All optimizations tested
- [Numba Optimization Results](optimizations/NUMBA_OPTIMIZATION_RESULTS.md) - JIT compilation gains
- [Final Numba Report](optimizations/FINAL_NUMBA_OPTIMIZATION_REPORT.md) - Complete optimization details
- [Quick Reference](optimizations/QUICK_REFERENCE.md) - Performance optimization quick guide
- [Deliverables Summary](optimizations/DELIVERABLES_SUMMARY.md) - What was built

### Regime Detection
- [Regime Integration Guide](regime/REGIME_INTEGRATION_GUIDE.md) - Complete integration documentation
- [Regime Quickstart](regime/REGIME_QUICKSTART.md) - Quick reference for regime filtering
- [Regime Code Changes](regime/REGIME_CODE_CHANGES.md) - Code modifications documented
- [Regime Integration Report](regime/REGIME_INTEGRATION_REPORT.md) - Technical benchmarks
- [Regime Integration Summary](regime/REGIME_INTEGRATION_SUMMARY.md) - Executive summary
- [Regime Detection Summary](regime/REGIME_DETECTION_SUMMARY.md) - Detection algorithm details
- [Regime Files Index](regime/REGIME_FILES_INDEX.txt) - File organization

### Edge Cases & Testing
- [Critical Edge Cases Summary](edge-cases/CRITICAL_EDGE_CASES_SUMMARY.md) - Important edge cases
- [Edge Case Analysis Report](edge-cases/EDGE_CASE_ANALYSIS_REPORT.md) - Comprehensive analysis
- [Edge Case Quick Reference](edge-cases/EDGE_CASE_QUICK_REFERENCE.md) - Quick lookup

### User Interface
- [Streamlit UI Architecture](STREAMLIT_UI_ARCHITECTURE.md) - UI design and structure
- [UI User Guide](UI_USER_GUIDE.md) - How to use the web interface

### Database & Infrastructure
- [PostgreSQL Setup](../README-POSTGRESQL.md) - PostgreSQL configuration for distributed optimization
- [Optuna Optimization Improvements](OPTUNA_OPTIMIZATION_IMPROVEMENTS.md) - Hyperparameter tuning guide

## Directory Structure

```
docs/
├── README.md (this file)
├── architecture/           # System architecture documentation
├── edge-cases/            # Edge case analysis and testing
├── optimizations/         # Performance optimization reports
├── regime/               # Regime detection documentation
├── STRATEGY_DEVELOPMENT_GUIDE.md
├── STRATEGY_REQUIREMENTS_SPECIFICATION.md
├── STREAMLIT_UI_ARCHITECTURE.md
├── UI_USER_GUIDE.md
└── OPTUNA_OPTIMIZATION_IMPROVEMENTS.md
```

## Getting Help

1. **Quick Questions**: Check the quickstart guides
2. **Strategy Development**: Read [STRATEGY_GUIDE.md](../STRATEGY_GUIDE.md) in root
3. **Performance Issues**: See [optimizations/](optimizations/)
4. **System Architecture**: See [architecture/](architecture/)
5. **Advanced Features**: Check specific feature documentation

## Version Information

- **System Version**: 2.0 (Optimized)
- **Last Updated**: 2025-11-20
- **Python Version**: 3.11.9
- **Key Dependencies**: NumPy, Pandas, Optuna, Numba, Streamlit

## Performance Summary

Current system capabilities:
- **Backtest Speed**: 4x faster (0.12ms per backtest)
- **Position Management**: 16x faster (Numba-compiled)
- **Trial Throughput**: 31.8 trials/minute
- **Optimization Efficiency**: 81% fewer wasted trials (aggressive preset)
- **Memory Usage**: ~500MB stable
- **Regime Detection**: 16,700 bars/second

## Production Features

- ✅ Headless Linux deployment
- ✅ Optional Streamlit UI
- ✅ PostgreSQL distributed optimization
- ✅ Regime-based market filtering
- ✅ Multi-strategy support
- ✅ Walk-forward validation
- ✅ Prop firm rule compliance
- ✅ Comprehensive testing framework
