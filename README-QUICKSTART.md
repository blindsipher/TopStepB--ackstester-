# Backtestester / TopStepB – Quickstart
Author: blindsipher

This is a concise setup and usage guide for the trading research/optimization pipeline found in the `TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY` folder.

- Python: 3.11–3.13 recommended
- OS: Windows or Linux
- Data: CSV or Parquet supported (Parquet requires `pyarrow`)

## 1) Install Dependencies

```
pip install -r requirements.txt
```

Optional dev tools:
- Uncomment `pytest` in `requirements.txt` if you want to run tests.

## 2) Run A Quick Optimization (Synthetic Data)

The primary entry point is `main_runner.py` inside the TopStepB folder (note the space in the path on Windows).

Windows (PowerShell):
```
python "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY\main_runner.py" \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 5m \
  --split-type walk_forward \
  --synthetic-bars 5000 \
  --max-trials 50 \
  --max-workers 2
```

Linux/macOS:
```
python "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/main_runner.py" \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 5m \
  --split-type walk_forward \
  --synthetic-bars 5000 \
  --max-trials 50 \
  --max-workers 2
```

## 3) Run With Your Data (CSV/Parquet)

You can load CSV or Parquet files. The loader normalizes column names and ensures a `datetime` column with timezone handling.

Examples:
```
# CSV
python "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/main_runner.py" \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 5m \
  --data-file ".\data\your_file.csv" \
  --max-trials 100

# Parquet (requires pyarrow)
python "TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/main_runner.py" \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 5m \
  --data-file ".\data\your_file.parquet" \
  --max-trials 100
```

## 4) Optional: PostgreSQL Storage for Optuna

By default, the engine will try PostgreSQL and fall back to SQLite automatically. To use PostgreSQL, ensure it is running and accessible; the storage parameters can be configured in `optimization/config/optuna_config.py`.

If PostgreSQL isn’t available, no action is required—SQLite will be used automatically in the run results folder.

## 5) Outputs

- Local tear sheets: `tear_sheets/`
- Logs and results (default): `%USERPROFILE%/.topstep_engine/{logs,results,...}` on Windows or `$HOME/.topstep_engine/...` on Linux/macOS

## 6) Run Tests (Optional)

```
pip install pytest  # or uncomment in requirements.txt
pytest -q
```

## 7) Troubleshooting

- Parquet read/write errors: make sure `pyarrow` is installed.
- PostgreSQL connection issues: verify credentials and port in `optimization/config/optuna_config.py`.
- Paths with spaces (Windows): wrap the full path in quotes, as shown above.
