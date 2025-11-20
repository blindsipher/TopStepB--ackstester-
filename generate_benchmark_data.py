"""
Generate synthetic data for benchmarking purposes.

This script creates a realistic synthetic OHLCV dataset that can be used
for performance benchmarking without requiring actual market data.
"""

import sys
from pathlib import Path

# Add project root and TopStepB to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'TopStepB'))

from data.data_loader import create_synthetic_data

def main():
    print("Generating synthetic benchmark data...")

    # Generate enough data for meaningful walk-forward splits
    # 10,000 bars of 1-minute data = ~1 week of trading
    data = create_synthetic_data(
        bars=10000,
        symbol="MNQ",
        timeframe="1min",
        base_price=16000.0
    )

    # Create data directory if it doesn't exist
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)

    # Save as parquet for fast loading
    output_path = data_dir / 'synthetic_benchmark_data.parquet'
    data.to_parquet(output_path, index=False)

    print(f"✅ Generated {len(data)} bars")
    print(f"   Date range: {data['datetime'].min()} to {data['datetime'].max()}")
    print(f"   Price range: {data['close'].min():.2f} to {data['close'].max():.2f}")
    print(f"   Saved to: {output_path}")
    print()
    print(f"Now run: python benchmark_performance.py --data {output_path.relative_to(Path(__file__).parent)}")

if __name__ == '__main__':
    main()
