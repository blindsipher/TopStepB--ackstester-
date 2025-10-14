"""
View detailed metrics for optimization trials
Shows what information is actually available beyond the composite score
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.services.database_service import DatabaseService
import pandas as pd

db = DatabaseService()

print("\n" + "="*60)
print("TRIAL METRICS VIEWER")
print("="*60)

# Get all studies
studies = db.list_studies(limit=10)

if not studies:
    print("\nNo studies found in database")
    sys.exit(0)

print(f"\nFound {len(studies)} studies:")
for i, study in enumerate(studies, 1):
    print(f"{i}. {study['study_name']}")

# Get best trial from first study
study_name = studies[0]['study_name']
print(f"\nAnalyzing study: {study_name}")
print("-"*60)

# Get best trial
best_trial = db.get_best_trial(study_name)

if not best_trial:
    print("No completed trials found")
    sys.exit(0)

print(f"\nBest Trial #{best_trial['number']}:")
print(f"  Score: {best_trial['value']:.4f}")
print(f"  State: {best_trial['state']}")
print(f"  Completed: {best_trial['datetime_complete']}")

# Get parameters
params = db.get_trial_parameters(study_name, best_trial['number'])

print(f"\n  Parameters ({len(params)} total):")
for k, v in sorted(params.items())[:5]:
    print(f"    {k}: {v}")
print(f"    ... ({len(params)-5} more parameters)")

# Check what's in user_attrs (this might have the detailed metrics)
print("\n" + "-"*60)
print("Checking database for detailed metrics...")
print("-"*60)

conn = db.get_connection()

# Query for user_attrs which might contain detailed metrics
query = """
SELECT t.number, tv.value, t.user_attrs, t.system_attrs
FROM trials t
JOIN studies s ON t.study_id = s.study_id
LEFT JOIN trial_values tv ON t.trial_id = tv.trial_id
WHERE s.study_name = %s AND t.state = 'COMPLETE'
ORDER BY tv.value DESC
LIMIT 1
"""

import psycopg2.extras
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
cursor.execute(query, (study_name,))
row = cursor.fetchone()
cursor.close()
db.return_connection(conn)

if row:
    print(f"\nTrial #{row['number']} Attributes:")
    print(f"  Composite Score: {row['value']:.4f}")

    if row['user_attrs']:
        print(f"\n  User Attributes:")
        import json
        try:
            attrs = json.loads(row['user_attrs']) if isinstance(row['user_attrs'], str) else row['user_attrs']
            for k, v in attrs.items():
                print(f"    {k}: {v}")
        except:
            print(f"    {row['user_attrs']}")
    else:
        print(f"\n  [NO USER ATTRIBUTES STORED]")

    if row['system_attrs']:
        print(f"\n  System Attributes:")
        try:
            attrs = json.loads(row['system_attrs']) if isinstance(row['system_attrs'], str) else row['system_attrs']
            for k, v in attrs.items():
                print(f"    {k}: {v}")
        except:
            print(f"    {row['system_attrs']}")
    else:
        print(f"\n  [NO SYSTEM ATTRIBUTES STORED]")

print("\n" + "="*60)
print("WHAT THIS MEANS")
print("="*60)

print("""
The composite score (0.709) is calculated from multiple metrics:
  - Profit Factor (30%)
  - Total PnL (25%)
  - TopStep Rules Pass (15%)
  - Win Rate (10%)
  - Sortino Ratio (10%)
  - Max Drawdown (5%)
  - Trade Frequency (5%)

However, the INDIVIDUAL metric values are not currently stored
in the database - only the final composite score.

TO SEE DETAILED METRICS, you need to:
1. Check if results are saved to files (JSON/CSV)
2. Re-run a trial with the best parameters
3. Add metric storage to the optimization code

Let me check if results files exist...
""")

# Check for results files
results_dir = project_root / "TopStepB" / "results"
if results_dir.exists():
    result_files = list(results_dir.glob("**/*.json")) + list(results_dir.glob("**/*.csv"))
    if result_files:
        print(f"\nFound {len(result_files)} result files:")
        for f in result_files[:5]:
            print(f"  - {f.name}")
        if len(result_files) > 5:
            print(f"  ... and {len(result_files)-5} more")
    else:
        print("\nNo result files found in results directory")
else:
    print("\nResults directory does not exist")
