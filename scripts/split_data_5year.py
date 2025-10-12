"""
Split large data files into 5-year chunks
More manageable than yearly, still under 200MB limit
"""
import pandas as pd
from pathlib import Path
import sys

def split_by_5year(input_file: str, output_dir: str):
    """
    Split data file into 5-year chunks

    Args:
        input_file: Path to large CSV file
        output_dir: Directory to save split files
    """
    print("\n" + "="*60)
    print("SPLITTING DATA INTO 5-YEAR CHUNKS")
    print("="*60)

    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get symbol and timeframe from filename
    filename_parts = input_path.stem.replace('_data', '').split('_')
    symbol = filename_parts[0]
    timeframe = filename_parts[1] if len(filename_parts) > 1 else '1m'

    print(f"\nReading: {input_path.name}")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")

    # Read the file
    df = pd.read_csv(input_file)
    df['datetime'] = pd.to_datetime(df['datetime'])

    total_rows = len(df)
    total_size_mb = input_path.stat().st_size / (1024 * 1024)

    print(f"\nTotal rows: {total_rows:,}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")

    # Get year range
    min_year = df['datetime'].dt.year.min()
    max_year = df['datetime'].dt.year.max()

    print(f"\nYears in data: {min_year} - {max_year}")

    # Define 5-year periods
    periods = []
    start = min_year
    while start <= max_year:
        end = min(start + 4, max_year)  # 5 years: start to start+4
        periods.append((start, end))
        start += 5

    print(f"\n5-year periods to create: {len(periods)}")
    for start, end in periods:
        print(f"  - {start}-{end}")

    # Split by periods
    print("\n" + "-"*60)
    print("Creating 5-year chunks...")
    print("-"*60)

    files_created = []

    for start_year, end_year in periods:
        # Filter data for this period
        period_data = df[
            (df['datetime'].dt.year >= start_year) &
            (df['datetime'].dt.year <= end_year)
        ].copy()

        if len(period_data) == 0:
            continue

        # Create output filename
        output_file = output_path / f"{symbol}_{timeframe}_{start_year}-{end_year}_data.csv"

        # Save to CSV
        period_data.to_csv(output_file, index=False)

        # Get file size
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        date_start = period_data['datetime'].min()
        date_end = period_data['datetime'].max()

        print(f"\n{start_year}-{end_year}:")
        print(f"  Rows: {len(period_data):,}")
        print(f"  Size: {file_size_mb:.2f} MB")
        print(f"  Date range: {date_start} to {date_end}")
        print(f"  File: {output_file.name}")

        if file_size_mb > 200:
            print(f"  [WARNING] Exceeds 200MB limit!")
        else:
            print(f"  [OK] Under 200MB limit")

        files_created.append({
            'period': f"{start_year}-{end_year}",
            'file': output_file,
            'rows': len(period_data),
            'size_mb': file_size_mb,
            'date_range': f"{date_start} to {date_end}"
        })

    # Summary
    print("\n" + "="*60)
    print("SPLIT COMPLETE")
    print("="*60)
    print(f"\nFiles created: {len(files_created)}")
    print(f"Output directory: {output_path}\n")

    total_output_size = sum(f['size_mb'] for f in files_created)
    print(f"Total output size: {total_output_size:.2f} MB")
    print(f"Average per file: {total_output_size / len(files_created):.2f} MB")

    # Check for oversized files
    large_files = [f for f in files_created if f['size_mb'] > 200]
    if large_files:
        print(f"\n[WARNING] {len(large_files)} files exceed 200MB:")
        for f in large_files:
            print(f"  - {f['period']}: {f['size_mb']:.2f} MB")
    else:
        print(f"\n[OK] All files are under 200MB and ready for UI upload")

    # Show usage instructions
    print("\n" + "="*60)
    print("USAGE INSTRUCTIONS")
    print("="*60)
    print("\nRecommended testing approach:")
    print("1. Recent validation:  Use most recent period for quick testing")
    print("2. Out-of-sample:      Train on one period, test on next period")
    print("3. Multi-period test:  Upload multiple periods sequentially")

    print("\nFiles created:")
    for f in files_created:
        print(f"  {f['file'].name}: {f['size_mb']:.1f}MB, {f['rows']:,} rows")

    return files_created

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted\MES_1m_data.csv"
    OUTPUT_DIR = r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted\5year"

    # Check if file exists
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        sys.exit(1)

    # Split into 5-year chunks
    split_by_5year(INPUT_FILE, OUTPUT_DIR)
