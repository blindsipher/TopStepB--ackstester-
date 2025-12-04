# TopStepB Configuration Guide

**Reference:** All configuration values based on actual code inspection.

---

## Quick Reference

```bash
# Minimal command
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol MES \
  --timeframe 1m \
  --account-type topstep_50k \
  --slippage 0.25 \
  --commission 2.5 \
  --contracts-per-trade 1 \
  --split-type chronological

# Full command with all options
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
  --data-file data/mes-1m.csv \
  --synthetic-bars 10000 \
  --max-trials 100 \
  --max-workers 4 \
  --memory-per-worker-mb 2000 \
  --timeout-per-trial 300 \
  --results-top-n 10 \
  --validation-tests in_sample,out_of_sample
```

---

## CLI Arguments

### Required Arguments

#### `--strategy` (string)
Strategy name to optimize.

**Format:** `{strategy_name}`
**Example:** `--strategy bollinger_squeeze`
**Location:** Must exist in `TopStepB/strategies/{strategy_name}/`

**Available strategies:**
```bash
# List available strategies
ls TopStepB/strategies/
# Current: bollinger_squeeze
```

#### `--symbol` (string)
Trading instrument symbol.

**Supported:** `ES`, `MES`, `NQ`, `MNQ` (pre-configured)
**Example:** `--symbol MES`

**Custom symbols:** Add to `TopStepB/config/system_config.py:TopStepMarkets`

#### `--timeframe` (string)
Bar timeframe for data.

**Format:** `{number}{unit}`
**Units:** `m` (minutes), `h` (hours), `d` (days)
**Examples:**
- `--timeframe 1m` (1 minute)
- `--timeframe 5m` (5 minutes)
- `--timeframe 15m` (15 minutes)
- `--timeframe 1h` (1 hour)
- `--timeframe 1d` (1 day)

#### `--account-type` (string)
Account configuration for position sizing and risk limits.

**Available:**
- `topstep_50k` - $50K starting capital, $3K profit target
- `topstep_100k` - $100K starting capital, $6K profit target
- `topstep_150k` - $150K starting capital, $9K profit target

**Example:** `--account-type topstep_50k`

**Configuration:** `TopStepB/config/system_config.py:TopStepAccounts`

#### `--slippage` (float)
Slippage in ticks per trade.

**Range:** 0.0 - 10.0 ticks
**Typical:** 0.25 - 1.0 ticks
**Example:** `--slippage 0.25`

**Calculation:**
```python
slippage_cost = slippage_ticks × tick_value
# MES: 0.25 ticks × $1.25 = $0.3125 per trade
# ES:  0.25 ticks × $12.50 = $3.125 per trade
```

#### `--commission` (float)
Commission per trade (round-trip).

**Range:** $0.00 - $10.00
**Typical:** $2.00 - $5.00
**Example:** `--commission 2.5`

**Total execution cost:**
```python
total_cost = commission + (slippage_ticks × tick_value)
# MES: $2.50 + (0.25 × $1.25) = $2.81 per round-trip
```

#### `--contracts-per-trade` (int)
Fixed position size in contracts.

**Range:** 1 - 10 contracts
**Default:** 1
**Example:** `--contracts-per-trade 1`

**Impact:** Scales P&L linearly (2 contracts = 2× profit/loss)

#### `--split-type` (choice)
Data splitting method.

**Options:**
- `chronological` - Single train/val/test split
- `walk_forward` - Rolling window analysis

**Example:** `--split-type chronological`

**Chronological:**
```
|---------- Train (60%) ----------|--- Val (20%) ---|--- Test (20%) ---|
```

**Walk-Forward:**
```
Window 1: |--- Train ---|-- Val --|-- Test --|
Window 2:               |--- Train ---|-- Val --|-- Test --|
Window 3:                             |--- Train ---|-- Val --|-- Test --|
```

---

### Optional Arguments

#### `--split-ratios` (float,float,float)
Train/validation/test split ratios.

**Format:** `train,validation,test` (must sum to 1.0)
**Default:** `0.6,0.2,0.2`
**Example:** `--split-ratios 0.6,0.2,0.2`

**Common configurations:**
- `0.6,0.2,0.2` - Standard (60% train, 20% val, 20% test)
- `0.7,0.15,0.15` - More training data
- `0.5,0.25,0.25` - More validation/test data

#### `--gap-days` (int)
Gap days between splits to prevent temporal leakage.

**Range:** 0 - 10 days
**Default:** 1
**Recommended:** 1-5 days
**Example:** `--gap-days 1`

**Purpose:** Prevents data leakage when market data has autocorrelation.

```
Train ends: 2024-01-31
Gap: 1 day (skip 2024-02-01)
Validation starts: 2024-02-02
```

#### `--data-file` (path)
Path to market data file.

**Formats:** CSV, Parquet
**Example:** `--data-file data/mes-1m-2024.csv`

**Required columns:**
- `timestamp` - DateTime or parseable string
- `open` - Opening price
- `high` - High price
- `low` - Low price
- `close` - Closing price
- `volume` - Trading volume

**If omitted:** Uses synthetic data (see `--synthetic-bars`)

#### `--synthetic-bars` (int)
Number of synthetic bars to generate (if no data file).

**Range:** 1,000 - 1,000,000
**Default:** 5,000
**Example:** `--synthetic-bars 10000`

**Generation:** Uses geometric Brownian motion with realistic OHLCV patterns.

#### `--optimization-enabled` / `--no-optimization` (flag)
Enable/disable parameter optimization.

**Default:** Enabled
**Example:** `--no-optimization`

**When disabled:** Uses default parameters from `parameters.py`

#### `--max-trials` (int)
Maximum optimization trials to run.

**Range:** 10 - 50,000
**Default:** 100
**Example:** `--max-trials 1000`

**Guidelines:**
- Development: 10-50 trials
- Testing: 100-500 trials
- Production: 1,000-10,000 trials

**Runtime estimate:**
```
10 trials × 4 workers = ~2 minutes
100 trials × 4 workers = ~15 minutes
1,000 trials × 16 workers = ~2 hours
```

#### `--max-workers` (int)
Maximum parallel workers for optimization.

**Range:** 1 - 64 (unlimited with PostgreSQL)
**Default:** CPU count - 1 (typically 9 on 10-core systems)
**Example:** `--max-workers 4`

**Scaling:**
- Local development: 2-4 workers
- Workstation: 8-16 workers
- AWS/Cloud: 32-64+ workers

**Memory requirement:** `workers × memory_per_worker_mb`

#### `--memory-per-worker-mb` (int)
Memory limit per worker process.

**Range:** 512 - 8192 MB
**Default:** 1500 MB
**Recommended:** 2000-3000 MB
**Example:** `--memory-per-worker-mb 2000`

**Total memory:** `workers × memory_per_worker_mb`
```bash
# 4 workers × 2GB = 8GB total
--max-workers 4 --memory-per-worker-mb 2000
```

#### `--timeout-per-trial` (int)
Maximum seconds per optimization trial.

**Range:** 10 - 3600 seconds
**Default:** 60 seconds
**Example:** `--timeout-per-trial 300`

**Guidelines:**
- Small datasets (<10K bars): 30-60 seconds
- Medium datasets (10K-100K bars): 60-300 seconds
- Large datasets (>100K bars): 300-600 seconds

#### `--results-top-n` (int)
Number of top parameter sets to deploy and validate.

**Range:** 1 - 100
**Default:** 10
**Example:** `--results-top-n 3`

**Impact:** Creates N deployed strategy files for validation.

#### `--validation-tests` (string)
Comma-separated list of validation tests to run.

**Options:**
- `in_sample` - Train+validation performance
- `out_of_sample` - Test data performance (critical)
- `in_sample_permutation` - Overfitting detection
- `out_of_sample_permutation` - Robustness test
- `monte_carlo` - Random entry simulation
- `regime_testing` - Performance across market regimes
- `noise_injection` - Sensitivity to data noise
- `all` - Run all tests

**Default:** `in_sample,out_of_sample`
**Example:** `--validation-tests in_sample,out_of_sample,monte_carlo`

**Runtime impact:** Each additional test adds ~10-20% to validation time.

---

## Environment Variables

**No environment variables required.** All configuration via CLI arguments or interactive mode.

**Optional PostgreSQL configuration:**
Edit `TopStepB/optimization/config/optuna_config.py`:

```python
@dataclass
class StorageConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "topstepb_optimization"
    username: str = "postgres"
    password: str = "your_password"
```

**Fallback:** Automatically uses SQLite if PostgreSQL unavailable.

---

## Optimization Configuration

**File:** `TopStepB/optimization/config/optuna_config.py`

### TPE Sampler Configuration

```python
@dataclass
class TPESamplerConfig:
    n_startup_trials: int = 50      # Random trials before TPE starts
    multivariate: bool = True       # Detect parameter correlations
    group: bool = True              # Handle mixed parameter types
    prior_weight: float = 1.0       # Regularization strength
    consider_prior: int = 25        # Recent trials to consider
    seed: int = 42                  # Reproducibility
```

**Tuning:**
- Increase `n_startup_trials` (100-200) for complex strategies
- Decrease `n_startup_trials` (20-30) for simple strategies
- Set `seed` for reproducible results

### Median Pruner Configuration

```python
@dataclass
class MedianPrunerConfig:
    n_startup_trials: int = 50      # Trials before pruning starts
    n_warmup_steps: int = 10        # Steps before pruning
    interval_steps: int = 5         # Pruning frequency
    n_min_trials: int = 5           # Minimum trials for pruning
```

**Tuning:**
- Increase `n_startup_trials` to prevent premature pruning
- Decrease `interval_steps` for more aggressive pruning

### Composite Score Weights

```python
@dataclass
class CompositeScoreWeights:
    # Profitability (55% total)
    profit_factor: float = 0.30     # Must exceed 1.0
    pnl: float = 0.25               # Dollar returns

    # Confidence (15% total)
    win_rate: float = 0.10          # Consistency
    trade_frequency: float = 0.05   # Activity level

    # Risk-adjusted (25% total)
    prop_firm_viability: float = 0.15  # TopStep compliance
    sortino_ratio: float = 0.10     # Downside risk

    # Risk management (5% total)
    max_drawdown: float = 0.05      # Capital preservation
```

**Customization:**
Edit weights in `optuna_config.py:CompositeScoreWeights` to prioritize different metrics.

**Constraints:**
- All weights must sum to 1.0
- Each weight 0.0 - 1.0

---

## Market Configuration

**File:** `TopStepB/config/system_config.py`

### Pre-configured Markets

```python
class TopStepMarkets:
    ES = MarketSpec(
        symbol='ES',
        tick_size=0.25,
        tick_value=12.50,
        margin_requirement=14300.0,
        description='E-mini S&P 500'
    )

    MES = MarketSpec(
        symbol='MES',
        tick_size=0.25,
        tick_value=1.25,
        margin_requirement=1430.0,
        description='Micro E-mini S&P 500'
    )

    NQ = MarketSpec(
        symbol='NQ',
        tick_size=0.25,
        tick_value=5.00,
        margin_requirement=18700.0,
        description='E-mini NASDAQ-100'
    )

    MNQ = MarketSpec(
        symbol='MNQ',
        tick_size=0.25,
        tick_value=0.50,
        margin_requirement=1870.0,
        description='Micro E-mini NASDAQ-100'
    )
```

### Adding Custom Markets

```python
# In system_config.py
CL = MarketSpec(
    symbol='CL',
    tick_size=0.01,
    tick_value=10.00,
    margin_requirement=5000.0,
    description='Crude Oil Futures'
)
```

---

## Account Configuration

**File:** `TopStepB/config/system_config.py`

### TopStep Accounts

```python
class TopStepAccounts:
    TOPSTEP_50K = AccountConfig(
        starting_capital=50000.0,
        daily_loss_limit=1000.0,
        max_drawdown=2000.0,
        profit_target=3000.0
    )

    TOPSTEP_100K = AccountConfig(
        starting_capital=100000.0,
        daily_loss_limit=2000.0,
        max_drawdown=4000.0,
        profit_target=6000.0
    )

    TOPSTEP_150K = AccountConfig(
        starting_capital=150000.0,
        daily_loss_limit=3000.0,
        max_drawdown=6000.0,
        profit_target=9000.0
    )
```

**Compliance checks:**
- Daily loss limit: Strategy must not exceed
- Max drawdown: Peak-to-trough loss limit
- Profit target: Required profit to pass evaluation

---

## Performance Tuning

### For Speed

```bash
# Maximize workers, minimize trials
--max-workers 16 \
--max-trials 500 \
--timeout-per-trial 60

# Use PostgreSQL for distributed optimization
# (Edit optuna_config.py with PostgreSQL credentials)
```

### For Accuracy

```bash
# More trials, longer timeout
--max-trials 10000 \
--timeout-per-trial 300 \
--max-workers 4

# More validation tests
--validation-tests all
```

### For Memory-Constrained Systems

```bash
# Reduce workers and memory
--max-workers 2 \
--memory-per-worker-mb 1500 \
--max-trials 100
```

### For Development/Testing

```bash
# Quick iterations
--max-trials 10 \
--max-workers 2 \
--synthetic-bars 5000 \
--validation-tests in_sample,out_of_sample
```

---

## Common Configurations

### Local Development

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
  --synthetic-bars 10000 \
  --max-trials 10 \
  --max-workers 2
```

### Production Optimization

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
  --split-ratios 0.6,0.2,0.2 \
  --gap-days 1 \
  --max-trials 5000 \
  --max-workers 16 \
  --memory-per-worker-mb 3000 \
  --timeout-per-trial 300 \
  --results-top-n 10 \
  --validation-tests all
```

### Walk-Forward Analysis

```bash
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol MES \
  --timeframe 1m \
  --account-type topstep_50k \
  --slippage 0.25 \
  --commission 2.5 \
  --contracts-per-trade 1 \
  --split-type walk_forward \
  --data-file data/mes-1m-3years.parquet \
  --max-trials 1000 \
  --max-workers 8 \
  --validation-tests in_sample,out_of_sample
```

---

## Configuration Files

### Strategy Parameters

**File:** `TopStepB/strategies/{strategy_name}/parameters.py`

```python
DEFAULT_PARAMETERS = {
    "bb_length": 20,
    "bb_std": 2.0,
    "kc_length": 20
}

PARAMETER_RANGES = {
    "bb_length": (10, 30, 1),     # min, max, step
    "bb_std": (1.5, 3.0, 0.1),
    "kc_length": (10, 30, 1)
}
```

**Modify:** To change optimization search space.

### Database Storage

**File:** `TopStepB/optimization/config/optuna_config.py`

```python
@dataclass
class StorageConfig:
    # PostgreSQL (distributed optimization)
    host: str = "localhost"
    port: int = 5432
    database: str = "topstepb_optimization"
    username: str = "postgres"
    password: str = "AdminAdmin"

    # Connection pool
    pool_size: int = 50
    max_overflow: int = 100
    pool_recycle: int = 3600
```

**Fallback:** SQLite in `results/optuna.db` if PostgreSQL unavailable.

---

## Troubleshooting

### Configuration Errors

**Symptom:** "Invalid split ratios"
```bash
ERROR: split_ratios must sum to 1.0
```
**Fix:** Ensure ratios sum to exactly 1.0:
```bash
--split-ratios 0.6,0.2,0.2  # ✅ Sums to 1.0
--split-ratios 0.6,0.3,0.2  # ❌ Sums to 1.1
```

**Symptom:** "Strategy not found"
```bash
ERROR: Strategy 'my_strategy' not found
```
**Fix:** Verify strategy directory exists:
```bash
ls TopStepB/strategies/my_strategy/
# Must contain: strategy.py, indicators.py, parameters.py, deployment_template.py
```

**Symptom:** "Insufficient memory"
```bash
ERROR: Worker crashed - out of memory
```
**Fix:** Reduce workers or increase memory:
```bash
--max-workers 2 --memory-per-worker-mb 3000
```

### Performance Issues

**Symptom:** Optimization too slow
```bash
# Increase workers
--max-workers 8

# Reduce trials
--max-trials 500

# Shorter timeout
--timeout-per-trial 60
```

**Symptom:** High memory usage
```bash
# Reduce workers
--max-workers 2

# Lower memory per worker
--memory-per-worker-mb 1500

# Use smaller dataset
--synthetic-bars 5000
```

---

## Interactive Mode

If no CLI arguments provided, interactive prompts collect configuration:

```bash
python TopStepB/main_runner.py

# Prompts:
Strategy name: bollinger_squeeze
Symbol: MES
Timeframe: 1m
Account type (topstep_50k/100k/150k): topstep_50k
Slippage (ticks): 0.25
Commission ($): 2.5
Contracts per trade: 1
Data file (Enter for synthetic):
Max trials: 10
Max workers: 4
```

**Tip:** Use interactive mode for quick testing, CLI for automation.

---

**Next Steps:**
- Read `docs/ARCHITECTURE.md` for system design
- Review `docs/VALIDATION.md` for testing framework
- See `SYSTEM_CAPABILITIES_FLOWMAP.md` for full technical details
