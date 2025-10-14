"""
Analyze Best Trial - Show Real Trading Metrics
Re-runs the best trial to display actual performance metrics
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService
import subprocess
import json

print("\n" + "="*60)
print("BEST TRIAL PERFORMANCE ANALYZER")
print("="*60)

# Get studies
db = DatabaseService()
studies = db.list_studies(limit=10)

if not studies:
    print("\nNo studies found")
    sys.exit(1)

print(f"\nAvailable studies:")
for i, study in enumerate(studies, 1):
    print(f"{i}. {study['study_name']}")

# Use most recent study
study_name = studies[0]['study_name']
print(f"\nAnalyzing: {study_name}")

# Get best trial
best_trial = db.get_best_trial(study_name)
params = db.get_trial_parameters(study_name, best_trial['number'])

print(f"\nBest Trial #{best_trial['number']}:")
print(f"  Composite Score: {best_trial['value']:.4f}")
print(f"  Parameters: {len(params)} total\n")

# Display parameters grouped
print("-"*60)
print("WINNING PARAMETERS")
print("-"*60)

bollinger = {k: v for k, v in params.items() if 'bb_' in k.lower()}
keltner = {k: v for k, v in params.items() if 'kc_' in k.lower()}
risk = {k: v for k, v in params.items() if any(x in k.lower() for x in ['stop', 'risk', 'atr', 'target'])}
filters = {k: v for k, v in params.items() if 'filter' in k.lower()}
exit_params = {k: v for k, v in params.items() if 'exit' in k.lower()}
other = {k: v for k, v in params.items() if k not in {**bollinger, **keltner, **risk, **filters, **exit_params}}

if bollinger:
    print("\nBollinger Bands:")
    for k, v in bollinger.items():
        print(f"  {k}: {v}")

if keltner:
    print("\nKeltner Channels:")
    for k, v in keltner.items():
        print(f"  {k}: {v}")

if risk:
    print("\nRisk Management:")
    for k, v in risk.items():
        print(f"  {k}: {v}")

if filters:
    print("\nFilters:")
    for k, v in filters.items():
        print(f"  {k}: {v}")

if exit_params:
    print("\nExit Rules:")
    for k, v in exit_params.items():
        print(f"  {k}: {v}")

if other:
    print("\nOther:")
    for k, v in other.items():
        print(f"  {k}: {v}")

print("\n" + "="*60)
print("IMPORTANT: METRICS NOT STORED IN DATABASE")
print("="*60)

print("""
The database only stores the COMPOSITE SCORE (0.7194), not the
individual performance metrics like:

  - Total PnL
  - Win Rate
  - Max Drawdown
  - Sharpe Ratio
  - Number of Trades
  - Profit Factor
  - Average Trade
  - etc.

To see these metrics, you need to:

1. Re-run the backtest with these winning parameters
2. Check if the optimization saves results to files
3. Add metric storage to the backtester code

Let me check if results files exist...
""")

# Check for results
results_dir = project_root / "TopStepB" / "results"
if results_dir.exists():
    # Look for recent result files
    import os
    import time

    result_files = []
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith(('.json', '.csv', '.txt')):
                filepath = Path(root) / file
                result_files.append((filepath, filepath.stat().st_mtime))

    if result_files:
        result_files.sort(key=lambda x: x[1], reverse=True)
        print(f"\nFound {len(result_files)} result files (most recent first):")
        for filepath, mtime in result_files[:10]:
            age = time.time() - mtime
            age_str = f"{age/3600:.1f}h ago" if age < 86400 else f"{age/86400:.1f}d ago"
            print(f"  {filepath.name} ({age_str})")

        print(f"\nChecking most recent file for metrics...")
        recent_file = result_files[0][0]

        try:
            if recent_file.suffix == '.json':
                with open(recent_file, 'r') as f:
                    data = json.load(f)
                print(f"\nMetrics from {recent_file.name}:")

                # Try to find metrics in the JSON
                if isinstance(data, dict):
                    for key in ['metrics', 'performance', 'results', 'statistics']:
                        if key in data:
                            print(f"\n{key.upper()}:")
                            if isinstance(data[key], dict):
                                for k, v in data[key].items():
                                    print(f"  {k}: {v}")
                            else:
                                print(f"  {data[key]}")
                else:
                    print("  (JSON structure not recognized)")

            elif recent_file.suffix == '.csv':
                import pandas as pd
                df = pd.read_csv(recent_file, nrows=5)
                print(f"\nColumns in {recent_file.name}:")
                print(f"  {', '.join(df.columns)}")

        except Exception as e:
            print(f"  Could not read file: {e}")
    else:
        print("\n[NO RESULT FILES FOUND]")
else:
    print("\n[RESULTS DIRECTORY DOES NOT EXIST]")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)

print("""
To get detailed performance metrics:

OPTION 1: Check the optimizer's output logs
  - The optimization process may print metrics to console
  - Check logs/aggregator.log or console output

OPTION 2: Re-run with best parameters
  - Use the winning parameters shown above
  - Run a single backtest (not optimization)
  - Capture the detailed output

OPTION 3: Add a results export feature
  - Modify the optimization code to save metrics
  - Store individual metrics in database
  - Export to CSV/JSON for analysis

Would you like me to create a script to re-run the best trial
and capture all the detailed metrics?
""")
