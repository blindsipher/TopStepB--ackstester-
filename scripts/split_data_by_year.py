"""
Split large data files into year-based chunks
Each chunk will be under 200MB for UI upload
"""
import pandas as pd
from pathlib import Path
import sys

def split_by_year(input_file: str, output_dir: str, max_size_mb: int = 180):
    """
    Split data file into yearly chunks under max_size_mb

    Args:
        input_file: Path to large CSV file
        output_dir: Directory to save split files
        max_size_mb: Maximum file size in MB (default 180 for safety margin)
    """
    print("\n" + "="*60)
    print("SPLITTING LARGE DATA FILE BY YEAR")
    print("="*60)

    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get symbol and timeframe from filename
    # Example: MES_1m_data.csv -> MES, 1m
    filename_parts = input_path.stem.replace('_data', '').split('_')
    symbol = filename_parts[0]
    timeframe = filename_parts[1] if len(filename_parts) > 1 else '1m'

    print(f"\nReading: {input_path.name}")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Target max size: {max_size_mb} MB")

    # Read the file
    df = pd.read_csv(input_file)
    df['datetime'] = pd.to_datetime(df['datetime'])

    total_rows = len(df)
    total_size_mb = input_path.stat().st_size / (1024 * 1024)

    print(f"\nTotal rows: {total_rows:,}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")

    # Add year column
    df['year'] = df['datetime'].dt.year

    # Get unique years
    years = sorted(df['year'].unique())
    print(f"\nYears in data: {years[0]} - {years[-1]} ({len(years)} years)")

    # Split by year
    print("\n" + "-"*60)
    print("Creating year-based splits...")
    print("-"*60)

    files_created = []

    for year in years:
        year_data = df[df['year'] == year].drop('year', axis=1)

        if len(year_data) == 0:
            continue

        # Create output filename
        output_file = output_path / f"{symbol}_{timeframe}_{year}_data.csv"

        # Save to CSV
        year_data.to_csv(output_file, index=False)

        # Get file size
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        print(f"{year}: {len(year_data):,} rows, {file_size_mb:.2f} MB -> {output_file.name}")

        # Check if still too large
        if file_size_mb > max_size_mb:
            print(f"  WARNING: Still too large! Needs further splitting by quarter/month")

        files_created.append({
            'year': year,
            'file': output_file,
            'rows': len(year_data),
            'size_mb': file_size_mb,
            'date_range': f"{year_data['datetime'].min()} to {year_data['datetime'].max()}"
        })

    # Summary
    print("\n" + "="*60)
    print("SPLIT COMPLETE")
    print("="*60)
    print(f"\nFiles created: {len(files_created)}")
    print(f"Output directory: {output_path}")

    total_output_size = sum(f['size_mb'] for f in files_created)
    print(f"\nTotal output size: {total_output_size:.2f} MB")
    print(f"Average per file: {total_output_size / len(files_created):.2f} MB")

    # Show files that are still too large
    large_files = [f for f in files_created if f['size_mb'] > max_size_mb]
    if large_files:
        print(f"\n[WARNING] {len(large_files)} files still exceed {max_size_mb}MB:")
        for f in large_files:
            print(f"  - {f['year']}: {f['size_mb']:.2f} MB")
        print("\nRecommendation: Split these years further by quarter or month")
    else:
        print(f"\n[OK] All files are under {max_size_mb}MB and ready for UI upload")

    return files_created

def split_year_by_quarter(input_file: str, year: int, output_dir: str):
    """Split a specific year into quarters"""
    print(f"\nSplitting {year} into quarters...")

    input_path = Path(input_file)
    output_path = Path(output_dir)

    # Get symbol and timeframe
    filename_parts = input_path.stem.replace('_data', '').split('_')
    symbol = filename_parts[0]
    timeframe = filename_parts[1] if len(filename_parts) > 1 else '1m'

    # Read the file
    df = pd.read_csv(input_file)
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Filter to specific year
    year_data = df[df['datetime'].dt.year == year].copy()
    year_data['quarter'] = year_data['datetime'].dt.quarter

    files_created = []

    for quarter in [1, 2, 3, 4]:
        quarter_data = year_data[year_data['quarter'] == quarter].drop('quarter', axis=1)

        if len(quarter_data) == 0:
            continue

        output_file = output_path / f"{symbol}_{timeframe}_{year}_Q{quarter}_data.csv"
        quarter_data.to_csv(output_file, index=False)

        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"  Q{quarter}: {len(quarter_data):,} rows, {file_size_mb:.2f} MB")

        files_created.append(output_file)

    return files_created

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted\MES_1m_data.csv"
    OUTPUT_DIR = r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted\split"

    # Check if file exists
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        sys.exit(1)

    # Split by year
    files = split_by_year(INPUT_FILE, OUTPUT_DIR, max_size_mb=180)

    # Check if any files are still too large and split by quarter
    large_files = [f for f in files if f['size_mb'] > 180]

    if large_files:
        print("\n" + "="*60)
        print("SPLITTING LARGE YEARS INTO QUARTERS")
        print("="*60)

        for file_info in large_files:
            split_year_by_quarter(
                str(file_info['file']),
                file_info['year'],
                OUTPUT_DIR
            )
            # Delete the large yearly file
            file_info['file'].unlink()
            print(f"Removed large file: {file_info['file'].name}")

    print("\n" + "="*60)
    print("ALL FILES READY FOR UPLOAD")
    print("="*60)
    print(f"\nLocation: {OUTPUT_DIR}")
    print("\nYou can now upload these files individually through the UI")
    print("or use them sequentially for multi-year backtests.")
