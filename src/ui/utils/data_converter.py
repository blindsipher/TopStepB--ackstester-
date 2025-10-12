"""
Data Conversion Utility
Converts semicolon-delimited files to backtester format and resamples to different timeframes
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

def convert_and_resample(input_file: str, output_dir: str, timeframe: str = '20T',
                         symbol: str = None, max_rows: int = None):
    """
    Convert semicolon-delimited data to backtester format

    Args:
        input_file: Path to input CSV file (semicolon-delimited, no headers)
        output_dir: Directory to save converted file
        timeframe: Pandas resample frequency (e.g., '20T' = 20 minutes, '1H' = 1 hour, '1D' = 1 day)
        symbol: Symbol name for output file (extracted from filename if None)
        max_rows: Maximum rows to process from input (None = all rows)
    """
    print(f"\n{'='*60}")
    print(f"Converting: {Path(input_file).name}")
    print(f"Timeframe: {timeframe}")
    print(f"{'='*60}\n")

    # Extract symbol from filename if not provided
    if symbol is None:
        symbol = Path(input_file).stem.split('-')[0].upper()

    # Read the semicolon-delimited file
    print("Step 1: Reading input file...")
    df = pd.read_csv(
        input_file,
        sep=';',
        names=['date', 'time', 'open', 'high', 'low', 'close', 'volume'],
        nrows=max_rows
    )

    print(f"  - Loaded {len(df):,} rows")
    print(f"  - Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")

    # Combine date and time into datetime
    print("\nStep 2: Converting to datetime...")
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'],
                                     dayfirst=True)

    # Drop original date and time columns
    df = df.drop(['date', 'time'], axis=1)

    # Reorder columns
    df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

    # Set datetime as index for resampling
    df.set_index('datetime', inplace=True)

    print(f"  - Datetime range: {df.index[0]} to {df.index[-1]}")

    # Resample to target timeframe
    if timeframe != '1T':
        print(f"\nStep 3: Resampling to {timeframe}...")
        df_resampled = df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Drop rows with NaN (periods with no data)
        df_resampled = df_resampled.dropna()

        print(f"  - Resampled to {len(df_resampled):,} rows")
        print(f"  - Data reduction: {len(df) / len(df_resampled):.1f}x")
    else:
        df_resampled = df
        print("\nStep 3: Skipping resampling (1-minute data)")

    # Reset index to make datetime a column again
    df_resampled.reset_index(inplace=True)

    # Create output filename
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{symbol}_{timeframe.replace('T', 'm').replace('H', 'h').replace('D', 'd')}_data.csv"

    # Save to CSV
    print(f"\nStep 4: Saving to {output_file.name}...")
    df_resampled.to_csv(output_file, index=False)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"  - Output file size: {file_size_mb:.2f} MB")

    print(f"\n{'='*60}")
    print(f"[OK] Conversion complete: {output_file}")
    print(f"{'='*60}\n")

    return df_resampled

def convert_all_files(input_dir: str, output_dir: str, timeframes: list = ['20T', '1H'],
                      max_rows: int = None):
    """
    Convert all CSV files in input directory

    Args:
        input_dir: Directory containing semicolon-delimited CSV files
        output_dir: Directory to save converted files
        timeframes: List of timeframes to generate (e.g., ['20T', '1H', '1D'])
        max_rows: Maximum rows to process from each input file (None = all rows)
    """
    input_path = Path(input_dir)
    csv_files = list(input_path.glob('*.csv'))

    print(f"\nFound {len(csv_files)} CSV files in {input_dir}")
    print(f"Timeframes to generate: {', '.join(timeframes)}")
    if max_rows:
        print(f"Processing first {max_rows:,} rows only (for testing)")
    print("\n")

    results = {}

    for csv_file in csv_files:
        symbol = csv_file.stem.split('-')[0].upper()
        results[symbol] = {}

        for timeframe in timeframes:
            try:
                df = convert_and_resample(
                    str(csv_file),
                    output_dir,
                    timeframe=timeframe,
                    symbol=symbol,
                    max_rows=max_rows
                )
                results[symbol][timeframe] = {
                    'status': 'success',
                    'rows': len(df),
                    'date_range': f"{df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}"
                }
            except Exception as e:
                print(f"ERROR processing {csv_file.name} at {timeframe}: {e}")
                results[symbol][timeframe] = {
                    'status': 'error',
                    'error': str(e)
                }

    # Print summary
    print("\n" + "="*60)
    print("CONVERSION SUMMARY")
    print("="*60)

    for symbol, timeframe_results in results.items():
        print(f"\n{symbol}:")
        for timeframe, result in timeframe_results.items():
            if result['status'] == 'success':
                print(f"  [OK] {timeframe}: {result['rows']:,} rows ({result['date_range']})")
            else:
                print(f"  [ERROR] {timeframe}: {result['error']}")

    print("\n" + "="*60)

if __name__ == "__main__":
    # Configuration
    INPUT_DIR = r"C:\Users\salte\ClaudeProjects\github-repos\00-trading-project\98-month-by-month-data-files\source files not for backtesting"
    OUTPUT_DIR = r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted"

    # Timeframes to generate
    TIMEFRAMES = ['1T', '20T', '1H', '4H', '1D']  # Added 1-minute for maximum accuracy

    # For initial testing, limit rows (remove for full conversion)
    MAX_ROWS = None  # Set to 100000 for testing, None for full conversion

    print("="*60)
    print("DATA CONVERSION UTILITY")
    print("="*60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("\nTEST MODE: Processing first 100,000 rows only")
        MAX_ROWS = 100000

    convert_all_files(INPUT_DIR, OUTPUT_DIR, TIMEFRAMES, MAX_ROWS)
