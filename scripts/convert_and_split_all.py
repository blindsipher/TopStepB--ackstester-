"""
Convert and split all symbols to 1-minute 5-year chunks
Processes: MCL, MGC, NG, SI (MES already done)
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.data_converter import convert_and_resample
import pandas as pd

def split_by_5year(input_file: str, output_dir: str, symbol: str, timeframe: str):
    """Split data file into 5-year chunks"""

    print(f"\nSplitting {symbol} into 5-year chunks...")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Read the file
    df = pd.read_csv(input_file)
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Get year range
    min_year = df['datetime'].dt.year.min()
    max_year = df['datetime'].dt.year.max()

    # Define 5-year periods
    periods = []
    start = min_year
    while start <= max_year:
        end = min(start + 4, max_year)
        periods.append((start, end))
        start += 5

    files_created = []

    for start_year, end_year in periods:
        period_data = df[
            (df['datetime'].dt.year >= start_year) &
            (df['datetime'].dt.year <= end_year)
        ].copy()

        if len(period_data) == 0:
            continue

        output_file = output_path / f"{symbol}_{timeframe}_{start_year}-{end_year}_data.csv"
        period_data.to_csv(output_file, index=False)

        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        status = "[OK]" if file_size_mb <= 200 else "[WARNING]"
        print(f"  {start_year}-{end_year}: {len(period_data):,} rows, {file_size_mb:.1f}MB {status}")

        files_created.append(output_file)

    return files_created

# Configuration
INPUT_DIR = Path(r"C:\Users\salte\ClaudeProjects\github-repos\00-trading-project\98-month-by-month-data-files\source files not for backtesting")
TEMP_DIR = Path(r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted")
OUTPUT_DIR = Path(r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted\5year")

# Symbols to process (MES already done)
SYMBOLS = ['MCL', 'MGC', 'NG', 'SI']

print("="*60)
print("BATCH CONVERSION AND SPLITTING")
print("="*60)
print(f"\nSymbols to process: {', '.join(SYMBOLS)}")
print("Steps per symbol:")
print("  1. Convert semicolon-delimited to proper CSV format")
print("  2. Split into 5-year chunks")
print("  3. Verify all files under 200MB\n")
print("="*60)

all_files_created = {}

for symbol in SYMBOLS:
    print(f"\n{'='*60}")
    print(f"PROCESSING: {symbol}")
    print(f"{'='*60}")

    # Find input file
    input_files = list(INPUT_DIR.glob(f"{symbol.lower()}*.csv"))
    if not input_files:
        print(f"ERROR: No file found for {symbol}")
        continue

    input_file = input_files[0]

    print(f"\nStep 1: Converting {input_file.name} to 1-minute format...")

    # Convert to 1-minute format
    try:
        df = convert_and_resample(
            str(input_file),
            str(TEMP_DIR),
            timeframe='1T',
            symbol=symbol,
            max_rows=None
        )

        temp_file = TEMP_DIR / f"{symbol}_1m_data.csv"

        print(f"\nStep 2: Splitting into 5-year chunks...")

        # Split into 5-year chunks
        files = split_by_5year(
            str(temp_file),
            str(OUTPUT_DIR),
            symbol,
            '1m'
        )

        all_files_created[symbol] = files

        print(f"\n[OK] {symbol} complete: {len(files)} files created")

    except Exception as e:
        print(f"\n[ERROR] Failed to process {symbol}: {e}")
        import traceback
        traceback.print_exc()
        continue

# Final summary
print("\n" + "="*60)
print("BATCH PROCESSING COMPLETE")
print("="*60)

print(f"\nOutput directory: {OUTPUT_DIR}")
print(f"\nSymbols processed: {len(all_files_created)}")

total_files = 0
for symbol, files in all_files_created.items():
    print(f"\n{symbol}: {len(files)} files")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name}: {size_mb:.1f}MB")
        total_files += 1

print(f"\nTotal files created: {total_files}")
print(f"\nAll files are in: {OUTPUT_DIR}")
print("\nReady for upload through the UI Data Loader!")
