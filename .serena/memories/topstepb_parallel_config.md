# TopStepB Parallel Processing Configuration

## Parallel Processing Overview

TopStepB uses PostgreSQL-backed Optuna for unlimited worker scalability with dynamic resource allocation.

## Configuration Files

### 1. Environment Variables
**File**: `.env.example` (copy to `.env`)

```bash
# Optimization Parallelization
OPTUNA_MAX_TRIALS=1000
OPTUNA_MAX_WORKERS=4          # Number of parallel workers
OPTUNA_RESULTS_TOP_N=50       # Top-N parameter sets to return
OPTUNA_MIN_TRADES=30          # Minimum trades threshold

# PostgreSQL Configuration (unlimited worker support)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=optuna_optimization
POSTGRES_USER=postgres
POSTGRES_PASSWORD=" "         # Single space character
```

### 2. Optuna Configuration
**File**: `TopStepB/optimization/config/optuna_config.py`

**Class**: `OptimizationLimits`

```python
@dataclass
class OptimizationLimits:
    max_trials: int = 50000              # Total trials (institutional scale)
    timeout_per_trial: int = 300         # Max seconds per trial
    max_optimization_time: int = 28800   # 8 hours total
    results_top_n: int = 500             # Top-N parameter sets (1-500)
    memory_limit_mb: int = 1500          # Per-worker memory limit
    max_workers: int = 0                 # 0 = auto-detect CPU cores
    checkpoint_interval: int = 50        # Save every N trials
```

**Class**: `StorageConfig` (PostgreSQL)

```python
@dataclass
class StorageConfig:
    storage_type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "optuna_optimization"
    username: str = "postgres"
    password: str = " "
    
    # Dynamic connection pooling (scales with workers)
    pool_size: int = 60           # Base connections
    max_overflow: int = 120       # Burst capacity (2x pool_size)
    pool_timeout: int = 15        # Connection timeout
    pool_recycle: int = 3600      # Recycle after 1 hour
```

## OptunaEngine Worker Configuration

**File**: `TopStepB/optimization/engine.py`

**Method**: `OptunaEngine.run(pipeline_state)`

```python
# User-specified max_workers from CLI/config
opt_config = OptimizationConfig()
opt_config.limits.max_workers = state.max_workers  # CLI: --max-workers

# Create OptunaEngine
engine = OptunaEngine(config=opt_config)
optimization_result = engine.run(pipeline_state=state)
```

**Internal Flow**:
```python
# OptunaEngine._run_optimization()
max_workers = self.config.limits.max_workers or 1
safe_n_jobs = self._validate_postgresql_concurrency(max_workers)

if safe_n_jobs > 1:
    # Parallel optimization with PostgreSQL scalability
    self.parallel_optimizer.run_parallel_optimization(
        study=self.study,
        objective=objective_function,
        n_trials=self.config.limits.max_trials,
        n_jobs=max_workers,  # <-- CRITICAL: Worker count passed here
        timeout=self.config.limits.max_optimization_time
    )
else:
    # Single-threaded fallback
    self.study.optimize(objective_function, n_trials=n_trials)
```

## ParallelOptimizer Configuration

**File**: `TopStepB/optimization/parallel.py`

**Class**: `ParallelOptimizer`

**Initialization**:
```python
self.worker_config = {
    'max_workers': mp.cpu_count(),           # System CPU cores
    'safe_max_workers': mp.cpu_count(),      # Use ALL cores
    'memory_per_worker_mb': 1500,            # Empirical tuning
    'total_memory_limit_mb': optimized_total_memory_mb  # 90% system RAM
}
```

**Worker Validation**:
```python
def _validate_worker_count(self, requested_workers: int) -> int:
    cpu_count = mp.cpu_count()
    available_memory_mb = psutil.virtual_memory().available // (1024 * 1024)
    
    # Memory-based limit (1.25x safety factor)
    memory_per_worker = self.config.limits.memory_limit_mb
    memory_limited_workers = max(1, available_memory_mb // (memory_per_worker * 1.25))
    
    # Use most restrictive limit
    safe_workers = min(
        requested_workers,
        cpu_count,                    # Use ALL CPU cores
        memory_limited_workers        # Memory constraint
    )
    
    return max(1, safe_workers)
```

**Execution**:
```python
def run_parallel_optimization(self, study, objective, n_trials, n_jobs, ...):
    # Optuna's native parallelism (no manual ProcessPoolExecutor)
    study.optimize(
        objective,
        n_trials=n_trials,
        n_jobs=n_jobs,           # <-- CRITICAL: Worker count
        timeout=timeout,
        gc_after_trial=True,
        show_progress_bar=False
    )
```

## PostgreSQL Connection Pooling

**Dynamic Sizing**:
```python
# OptunaEngine._create_optuna_study()
expected_workers = self.config.limits.max_workers or mp.cpu_count()
optimized_pool_size = max(self.config.storage.pool_size, expected_workers + 10)
optimized_max_overflow = max(self.config.storage.max_overflow, optimized_pool_size)

engine_kwargs = {
    'pool_size': optimized_pool_size,        # Dynamic: workers + 10
    'max_overflow': optimized_max_overflow,  # 2x pool_size
    'pool_timeout': 15,
    'pool_recycle': 3600
}

storage = RDBStorage(url=database_url, engine_kwargs=engine_kwargs)
```

**High Concurrency Support**:
- Base pool: 60 connections
- Max overflow: 120 connections
- **Total capacity**: 180 concurrent connections
- **Worker support**: 150+ workers with connection sharing

## ValidationEngine Threading

**File**: `TopStepB/validation/engine.py`

**Class**: `ValidationEngine`

```python
def __init__(self, max_workers: int | None = None, ...):
    self.max_workers = max_workers or min(32, os.cpu_count() or 1)

def run(self, parameter_sets):
    workers = min(self.max_workers, len(params_list)) or 1
    with ThreadPoolExecutor(max_workers=workers) as exe:
        return list(exe.map(self._run_single, params_list))
```

**Threading Model**: Uses Python ThreadPoolExecutor (GIL-friendly for I/O-bound validation tasks)

## CLI Parameter Mapping

**File**: `TopStepB/app/pipeline.py` (from CLI args)

```python
# CLI: --max-workers 8
state.max_workers = 8  # User-specified

# CLI: --timeout-per-trial 300
state.timeout_per_trial = 300

# CLI: --memory-per-worker-mb 1500
state.memory_per_worker_mb = 1500

# CLI: --results-top-n 100
state.results_top_n = 100

# Pipeline reconnects to OptunaConfig
opt_config.limits.max_workers = state.max_workers
opt_config.limits.timeout_per_trial = state.timeout_per_trial
opt_config.limits.memory_limit_mb = state.memory_per_worker_mb
opt_config.limits.results_top_n = state.results_top_n
```

## Resource Monitoring

**Progress Monitoring**:
```python
# ParallelOptimizer._monitor_progress()
# Logs every 60 seconds:
# - Trials completed / target
# - Trials per minute
# - ETA
# - Memory usage (MB)
# - CPU usage (%)
```

**Resource Report**:
```python
parallel_optimizer.get_resource_usage_report()
# Returns: memory_total_mb, memory_available_mb, cpu_percent, active_workers
```

## Performance Scaling

**Example**: 8-core system, 32GB RAM
- **max_workers=8**: Full CPU utilization
- **Memory per worker**: 1500MB
- **Total memory**: 12GB (8 workers × 1500MB)
- **PostgreSQL pool**: 18 connections (8 workers + 10 buffer)
- **Throughput**: ~100-500 trials/minute (strategy-dependent)