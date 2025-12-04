# TopStepB Quickstart Guide

**Goal:** Run your first optimization in 5 minutes.

---

## Prerequisites

- Python 3.11+
- 8GB RAM minimum
- PostgreSQL 17 (optional, falls back to SQLite)

## Installation

```bash
# Clone and install
git clone <repo-url> TopStepB
cd TopStepB
pip install -r requirements.txt

# Verify installation
python -c "import vectorbt as vbt; import optuna; print('Ready!')"
```

## Run Your First Optimization

### Option 1: Interactive Mode (Recommended for First Run)

```bash
python TopStepB/main_runner.py
```

Follow the prompts:
1. Strategy: `bollinger_squeeze`
2. Symbol: `MES`
3. Timeframe: `1m`
4. Account: `topstep_50k`
5. Data: Press Enter to use synthetic data
6. Trials: `10` (quick test)

### Option 2: CLI Mode (Production)

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
  --synthetic-bars 10000 \
  --max-trials 10 \
  --max-workers 4 \
  --results-top-n 3
```

## What Happens

The 9-phase pipeline executes:

```
[1] Load Data → [2] Discover Strategy → [3] Trading Config → [4] Data Split
   ↓
[5] Optimization (Optuna + VectorBT) → 10 trials, 4 parallel workers
   ↓
[6] Deploy → Inject top-3 parameter sets into templates
   ↓
[7] Validate → Run in-sample + out-of-sample tests
   ↓
[8] Analytics → Rank validated strategies
   ↓
[9] Package → Assemble deployment artifacts
```

## Output Location

```
runs/bollinger_squeeze_MES_1m_YYYYMMDD_HHMMSS/
├── deployed_strategies/
│   ├── bollinger_squeeze_001.py  # Top parameter set
│   ├── bollinger_squeeze_002.py  # 2nd best
│   └── bollinger_squeeze_003.py  # 3rd best
├── validation_results.json
├── analytics_winners.json
└── logs/
```

## Quick Validation

```bash
# Check deployed strategy
python runs/.../deployed_strategies/bollinger_squeeze_001.py

# Expected: No errors (validation already ran)
```

## Next Steps

1. **Read Architecture**: `docs/ARCHITECTURE.md` - Understand the system
2. **Create Strategy**: `docs/STRATEGY_GUIDE.md` - Build your own
3. **Configure**: `docs/CONFIGURATION.md` - Tune parameters
4. **Production**: `SYSTEM_CAPABILITIES_FLOWMAP.md` - Full capabilities

## Common First-Run Issues

### PostgreSQL Not Found

```
WARNING: PostgreSQL unavailable, using SQLite
```

**Fix:** This is fine for local testing. For distributed optimization, setup PostgreSQL:
```bash
# See POSTGRESQL_VERIFIED.md for setup
```

### Low Memory Warning

```
ERROR: Worker crashed - insufficient memory
```

**Fix:** Reduce workers or increase memory:
```bash
--max-workers 2 --memory-per-worker-mb 2000
```

### No Strategy Found

```
ERROR: Strategy 'bollinger_squeeze' not found
```

**Fix:** Verify strategy directory:
```bash
ls TopStepB/strategies/bollinger_squeeze/
# Expected: strategy.py, indicators.py, parameters.py, deployment_template.py
```

## Performance Expectations

**10 trials, synthetic data (10K bars):**
- Duration: 30-60 seconds
- Memory: ~2GB
- CPU: 40-60% utilization (4 workers)

**100 trials, real data (100K bars):**
- Duration: 5-10 minutes
- Memory: ~4GB
- CPU: 80-90% utilization

**1000 trials, PostgreSQL (production):**
- Duration: 1-2 hours (16 workers)
- Memory: ~8GB total
- Database: 50-100MB storage

## Quick Commands Reference

```bash
# Interactive mode
python TopStepB/main_runner.py

# CLI with synthetic data
python TopStepB/main_runner.py --strategy bollinger_squeeze --symbol MES --max-trials 10

# CLI with real data
python TopStepB/main_runner.py --strategy bollinger_squeeze --data-file data/mes-1m.csv --max-trials 100

# Full production run
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --data-file data/mes-1m-5years.parquet \
  --max-trials 5000 \
  --max-workers 16 \
  --timeout-per-trial 300 \
  --results-top-n 10
```

## What You Just Did

1. Loaded/generated OHLCV market data
2. Discovered the Bollinger Squeeze strategy
3. Configured TopStep 50K account settings
4. Split data into train/validation/test
5. Ran 10 optimization trials using Optuna TPE sampler
6. VectorBT backtested each parameter set
7. Deployed top-3 parameter sets as executable Python files
8. Validated strategies on out-of-sample data
9. Ranked winners by composite score
10. Packaged results for deployment

**All in 30-60 seconds.**

---

**Next:** Read `docs/ARCHITECTURE.md` to understand what happened under the hood.
