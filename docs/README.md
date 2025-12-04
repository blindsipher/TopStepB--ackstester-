# TopStepB Documentation

**Welcome to the TopStepB institutional-grade trading strategy optimization system.**

---

## Quick Navigation

### Getting Started (5 minutes)
**[QUICKSTART.md](QUICKSTART.md)** - Run your first optimization in 5 minutes
- Installation
- First optimization (interactive mode)
- CLI mode usage
- Output explanation
- Common issues

### System Design
**[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture
- 9-phase pipeline flow
- Module structure
- VectorBT integration (2289x speedup)
- Data flow architecture
- Performance metrics
- System requirements

### Strategy Development
**[STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)** - Create trading strategies
- Dual-implementation model (vectorized + stateful)
- File structure requirements
- Sacred timing protocol (signal on close, execute on open)
- BaseStrategy contract
- VectorBT indicators
- Parity testing
- Common patterns

### Configuration
**[CONFIGURATION.md](CONFIGURATION.md)** - Configure the system
- CLI arguments reference
- Optimization configuration
- Market configuration
- Account configuration
- Performance tuning
- Common configurations
- Troubleshooting

### Validation
**[VALIDATION.md](VALIDATION.md)** - Testing and validation framework
- 7 validation tests
- PropFirm compliance checks
- Out-of-sample testing
- Metrics computation
- Pass/fail criteria
- Interpreting results
- Common issues

---

## Documentation Structure

```
docs/
├── README.md                           # This file - navigation hub
├── QUICKSTART.md                       # 5-minute getting started
├── ARCHITECTURE.md                     # System design and architecture
├── STRATEGY_GUIDE.md                   # Strategy development guide
├── CONFIGURATION.md                    # Configuration reference
├── VALIDATION.md                       # Validation framework
│
├── STRATEGY_DEVELOPMENT_GUIDE.md       # Detailed strategy guide (33KB)
├── STRATEGY_REQUIREMENTS_SPECIFICATION.md # Detailed requirements (26KB)
│
├── benchmarks/                         # Performance benchmark logs
│
└── archive/                            # Historical documentation
    ├── reports/                        # Phase completion reports
    │   ├── phase-completion/
    │   └── validation/
    └── analysis/                       # System analysis reports
```

---

## Documentation by Use Case

### "I want to run my first optimization"
→ **[QUICKSTART.md](QUICKSTART.md)**

### "I want to understand how the system works"
→ **[ARCHITECTURE.md](ARCHITECTURE.md)**

### "I want to create a new trading strategy"
→ **[STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)**

### "I want to tune optimization parameters"
→ **[CONFIGURATION.md](CONFIGURATION.md)**

### "I want to understand validation results"
→ **[VALIDATION.md](VALIDATION.md)**

### "I need detailed technical specifications"
→ **[STRATEGY_REQUIREMENTS_SPECIFICATION.md](STRATEGY_REQUIREMENTS_SPECIFICATION.md)**

### "I need complete system capabilities"
→ **[../SYSTEM_CAPABILITIES_FLOWMAP.md](../SYSTEM_CAPABILITIES_FLOWMAP.md)** (925 lines)

---

## Key Concepts

### 9-Phase Pipeline

```
[1] Data Loading → [2] Strategy Discovery → [3] Trading Config → [4] Data Split
                                    ↓
[5] Optimization (Optuna + VectorBT) → 100-50K trials, N workers
                                    ↓
           [6] Deployment → Inject top-N parameter sets
                                    ↓
         [7] Validation → 7 tests + PropFirm compliance
                                    ↓
              [8] Analytics → Rank validated strategies
                                    ↓
                [9] Package → Assemble deployment artifacts
```

### Dual-Implementation Model

Every strategy exists in TWO forms that MUST produce identical signals:

1. **Vectorized** (`strategy.py`) - For optimization (1000+ trials/min)
2. **Stateful** (`deployment_template.py`) - For live trading (bar-by-bar)

**Critical:** Use parity testing to verify implementations match.

### Sacred Timing Protocol

**"Signal on Close, Execute on Next Open"**

**Vectorized:**
```python
long_entry = indicator.shift(1) > threshold.shift(1)  # Use PREVIOUS bar
```

**Stateful:**
```python
if entry_condition:
    self.pending_entry_signal = 1  # Signal for NEXT bar
```

### VectorBT Integration

**Performance gains:**
- Bollinger Bands: 7x faster
- Keltner Channels: 12.8x faster
- ATR: 9.6x faster
- **IndicatorCache: 2289x faster** (compute once, reuse 5,000+ times)

### Data Leakage Prevention

**PipelineOrchestrator** enforces strict data segregation:
- **Optimization:** Train + validation ONLY (test withheld)
- **Validation:** Test data ONLY (out-of-sample)
- **Analytics:** Read-only full access
- **Gap days:** 1-5 days between splits

---

## System Status

**Production Status:** 94/100
**Tests:** 101/101 passing (100%)
**Performance:** 2289x speedup (IndicatorCache)
**Last Updated:** 2025-12-03

**Core Technologies:**
- VectorBT - Vectorized backtesting (100-2289x speedup)
- Optuna - TPE-based hyperparameter optimization
- PostgreSQL - Distributed coordination (falls back to SQLite)

---

## Quick Commands

### Interactive Mode
```bash
python TopStepB/main_runner.py
# Follow prompts for configuration
```

### CLI Mode (Quick Test)
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
  --max-trials 10
```

### CLI Mode (Production)
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
  --data-file data/mes-1m-5years.parquet \
  --max-trials 5000 \
  --max-workers 16 \
  --results-top-n 10 \
  --validation-tests all
```

---

## Common Questions

### Q: How do I add a new market?
**A:** Edit `TopStepB/config/system_config.py:TopStepMarkets`

```python
CL = MarketSpec(
    symbol='CL',
    tick_size=0.01,
    tick_value=10.00,
    margin_requirement=5000.0,
    description='Crude Oil Futures'
)
```

### Q: How do I create a new strategy?
**A:** See **[STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)** - Follow 4-file structure:
- `strategy.py` (vectorized)
- `indicators.py` (VectorBT indicators)
- `parameters.py` (ranges)
- `deployment_template.py` (stateful)

### Q: How do I speed up optimization?
**A:** See **[CONFIGURATION.md](CONFIGURATION.md)** - Performance tuning:
- Increase `--max-workers` (more parallel trials)
- Use PostgreSQL (distributed optimization)
- Enable IndicatorCache (automatic, 2289x speedup)

### Q: How do I interpret validation results?
**A:** See **[VALIDATION.md](VALIDATION.md)** - Pass criteria:
- Out-of-sample Sharpe ≥ 1.0
- Out-of-sample profit factor ≥ 1.1
- Degradation < 40%
- Beats permuted/random
- PropFirm compliance

### Q: Why does my strategy fail validation?
**A:** Common causes:
- Overfitting (high degradation)
- Look-ahead bias (missing .shift(1))
- PropFirm violations (aggressive sizing)
- Insufficient trades (< 100)

### Q: How do I setup PostgreSQL?
**A:** See **[../POSTGRESQL_VERIFIED.md](../POSTGRESQL_VERIFIED.md)** for setup guide.

### Q: What are the system requirements?
**A:** Minimum:
- Python 3.11+
- 8GB RAM
- 4 CPU cores
- PostgreSQL 17 (optional, falls back to SQLite)

---

## Performance Expectations

### Development (10 trials, synthetic data)
- **Duration:** 30-60 seconds
- **Memory:** ~2GB
- **CPU:** 40-60%

### Testing (100 trials, real data)
- **Duration:** 5-10 minutes
- **Memory:** ~4GB
- **CPU:** 80-90%

### Production (5,000 trials, 16 workers)
- **Duration:** 1-2 hours
- **Memory:** ~8GB total
- **CPU:** 95%
- **Database:** 50-100MB

---

## Troubleshooting

### PostgreSQL Not Found
```
WARNING: PostgreSQL unavailable, using SQLite
```
**Fix:** This is fine for local testing. For distributed optimization, see [POSTGRESQL_VERIFIED.md](../POSTGRESQL_VERIFIED.md)

### Strategy Not Found
```
ERROR: Strategy 'my_strategy' not found
```
**Fix:** Verify strategy directory exists:
```bash
ls TopStepB/strategies/my_strategy/
# Must contain: strategy.py, indicators.py, parameters.py, deployment_template.py
```

### Out of Memory
```
ERROR: Worker crashed - insufficient memory
```
**Fix:** Reduce workers or increase memory:
```bash
--max-workers 2 --memory-per-worker-mb 3000
```

### Validation Failed
```
ERROR: Strategy failed out_of_sample test
```
**Fix:** See **[VALIDATION.md](VALIDATION.md)** - Common issues section

---

## Architecture Highlights

### Module Breakdown

```
TopStepB/ (5,100 lines of production code)
├── main_runner.py (70 lines)          # Entry point
├── app/ (900 lines)                   # Pipeline orchestration
├── data/ (450 lines)                  # Data management
├── strategies/ (800 lines)            # Strategy framework
├── config/ (1,330 lines)              # System configuration
├── optimization/ (3,500 lines)        # Optimization engine
├── deployment/ (350 lines)            # Strategy deployment
├── validation/ (800 lines)            # Validation framework
├── analytics/ (300 lines)             # Winner selection
├── packager/ (150 lines)              # Result packaging
└── utils/ (450 lines)                 # Utilities
```

### Key Files

**Pipeline orchestration:**
- `app/pipeline.py` (457 lines) - 9-phase coordinator

**Optimization:**
- `optimization/engine.py` (630 lines) - OptunaEngine
- `optimization/objective.py` (2,414 lines) - StatefulObjective
- `optimization/vectorbt_engine.py` (250 lines) - VectorBT integration

**Configuration:**
- `config/system_config.py` (1,330 lines) - Market/account configuration
- `optimization/config/optuna_config.py` (200 lines) - Optimization settings

**Strategy example:**
- `strategies/bollinger_squeeze/strategy.py` (250 lines)
- `strategies/bollinger_squeeze/indicators.py` (150 lines)
- `strategies/bollinger_squeeze/deployment_template.py` (400 lines)

---

## Related Documentation

### In Repository Root

**[INDEX.md](../INDEX.md)** - Quick navigation index
**[README.md](../README.md)** - Project overview
**[SYSTEM_CAPABILITIES_FLOWMAP.md](../SYSTEM_CAPABILITIES_FLOWMAP.md)** - Complete system map (925 lines)

### PostgreSQL

**[POSTGRESQL_VERIFIED.md](../POSTGRESQL_VERIFIED.md)** - Database setup and verification

### Production Deployment

**[PRODUCTION_DEPLOYMENT_CHECKLIST.md](../PRODUCTION_DEPLOYMENT_CHECKLIST.md)** - AWS deployment guide

### VectorBT Integration

**[VECTORBT_INTEGRATION_COMPLETE.md](../VECTORBT_INTEGRATION_COMPLETE.md)** - VectorBT integration details

---

## Support

### Documentation Issues

If you find errors or gaps in documentation:
1. Check **[SYSTEM_CAPABILITIES_FLOWMAP.md](../SYSTEM_CAPABILITIES_FLOWMAP.md)** for technical details
2. Review archived docs in `docs/archive/` for additional context
3. Inspect actual code in `TopStepB/` directory

### Getting Help

1. **Quick questions:** See relevant doc above
2. **Configuration issues:** [CONFIGURATION.md](CONFIGURATION.md)
3. **Validation issues:** [VALIDATION.md](VALIDATION.md)
4. **Strategy development:** [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)
5. **Architecture questions:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Documentation Maintenance

**Last major update:** 2025-12-03
**Documentation structure:** Condensed from 150KB+ to 50KB of focused content

**Changes:**
- Archived old reports (docs/archive/reports/)
- Archived analysis files (docs/archive/analysis/)
- Removed non-existent UI documentation
- Created focused documentation:
  - QUICKSTART.md (5-minute guide)
  - ARCHITECTURE.md (system design)
  - STRATEGY_GUIDE.md (condensed from 2 guides)
  - CONFIGURATION.md (all configuration options)
  - VALIDATION.md (testing framework)
  - README.md (this navigation hub)

**Retained:**
- STRATEGY_DEVELOPMENT_GUIDE.md (detailed strategy guide)
- STRATEGY_REQUIREMENTS_SPECIFICATION.md (detailed requirements)
- All benchmark logs and historical reports (archived)

---

**Start here:** [QUICKSTART.md](QUICKSTART.md) → Run your first optimization in 5 minutes

**System overview:** [ARCHITECTURE.md](ARCHITECTURE.md) → Understand the 9-phase pipeline

**Build strategies:** [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md) → Create trading strategies

**Configure:** [CONFIGURATION.md](CONFIGURATION.md) → Tune optimization parameters

**Validate:** [VALIDATION.md](VALIDATION.md) → Ensure strategy robustness

---

**TopStepB:** Institutional-grade hyperparameter optimization for CME futures trading strategies.
