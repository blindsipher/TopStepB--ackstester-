"""
Convert specific symbol to 1-minute backtester format
For maximum SL/TP accuracy
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.data_converter import convert_and_resample

# Configuration
INPUT_DIR = Path(r"C:\Users\salte\ClaudeProjects\github-repos\00-trading-project\98-month-by-month-data-files\source files not for backtesting")
OUTPUT_DIR = Path(r"C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\data\converted")

# Choose symbol (MES, MCL, MGC, NG, SI)
SYMBOL = "MES"  # Change this to convert different symbols

input_file = INPUT_DIR / f"{SYMBOL.lower()}-1m_data.csv"

if not input_file.exists():
    print(f"ERROR: File not found: {input_file}")
    sys.exit(1)

print("\n" + "="*60)
print("1-MINUTE DATA CONVERSION (Maximum Accuracy)")
print("="*60)
print(f"\nConverting: {SYMBOL}")
print("Timeframe: 1-minute (no resampling)")
print("Expected rows: ~5.7 million")
print("Expected size: ~370 MB")
print("Processing time: 2-3 minutes")
print("\n" + "="*60 + "\n")

# Convert without resampling
df = convert_and_resample(
    str(input_file),
    str(OUTPUT_DIR),
    timeframe='1T',  # 1-minute = no resampling
    symbol=SYMBOL,
    max_rows=None  # Process all rows
)

print("\n" + "="*60)
print("CONVERSION COMPLETE")
print("="*60)
print(f"\nFile: {OUTPUT_DIR / f'{SYMBOL}_1m_data.csv'}")
print(f"Rows: {len(df):,}")
print(f"Date Range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
print("\nThis data provides maximum accuracy for:")
print("  - Stop loss execution")
print("  - Take profit execution")
print("  - Slippage modeling")
print("  - Intrabar price movement")
print("\n" + "="*60)
