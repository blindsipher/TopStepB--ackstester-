"""
Market Regime Detection Demo
============================

Quick demonstration of the regime detection system on realistic futures data.
Shows all key features in a single, easy-to-run script.

Author: Claude Code
Date: 2025-11-20
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from TopStepB.data.data_loader import create_synthetic_data
from TopStepB.data.regime_detector import (
    detect_regime,
    detect_regime_with_indicators,
    calculate_regime_statistics
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(title)
    print("="*70)


def main():
    """Run the regime detection demo."""

    print_section("MARKET REGIME DETECTION SYSTEM - DEMO")

    # Create realistic ES futures data
    print("\n1. Creating realistic ES futures data (3000 bars, 15-min)...")
    data = create_synthetic_data(bars=3000, symbol="ES", timeframe="15min")
    print(f"   ✓ Created {len(data)} bars")
    print(f"   ✓ Date range: {data['datetime'].min()} to {data['datetime'].max()}")
    print(f"   ✓ Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

    # Detect regimes
    print("\n2. Detecting market regimes...")
    regimes = detect_regime(data, lookback=100)
    print(f"   ✓ Classified {len(regimes)} bars")

    # Show distribution
    print("\n3. Regime Distribution:")
    print("-" * 70)
    regime_counts = regimes.value_counts()
    total = len(regimes)
    for regime, count in regime_counts.items():
        pct = count / total * 100
        bar = "█" * int(pct / 2)  # Visual bar chart
        print(f"   {regime:15s}: {count:4d} bars ({pct:5.1f}%) {bar}")

    # Calculate statistics
    print("\n4. Performance Metrics by Regime:")
    print("-" * 70)
    stats = calculate_regime_statistics(data, regimes)

    for regime in ['trending', 'mean_reverting', 'choppy']:
        metrics = stats[regime]
        if metrics['count'] > 0:
            print(f"\n   {regime.upper()}:")
            print(f"      Bars:         {metrics['count']:5d} ({metrics['percentage']:5.1f}%)")
            print(f"      Mean Return:  {metrics['mean_return']:7.4f}%")
            print(f"      Volatility:   {metrics['volatility']:7.4f}%")
            print(f"      Sharpe Ratio: {metrics['sharpe']:7.2f}")
            print(f"      Max Drawdown: {metrics['max_drawdown']:7.2f}%")

    # Show detailed indicators for recent bars
    print("\n5. Recent Regime Classifications (last 10 bars):")
    print("-" * 70)
    detailed = detect_regime_with_indicators(data, lookback=100)
    recent = detailed[['regime', 'adx', 'volatility', 'momentum', 'range_compression']].tail(10)
    recent_with_price = pd.DataFrame({
        'datetime': data['datetime'].tail(10).values,
        'close': data['close'].tail(10).values,
        'regime': recent['regime'].values,
        'adx': recent['adx'].values,
        'vol': recent['volatility'].values,
        'mom': recent['momentum'].values
    })
    print(recent_with_price.to_string(index=False))

    # Regime transitions
    print("\n6. Regime Transition Analysis:")
    print("-" * 70)
    transitions = (regimes != regimes.shift()).sum()
    transition_rate = transitions / len(regimes) * 100
    print(f"   Total transitions: {transitions}")
    print(f"   Transition rate:   {transition_rate:.2f}%")

    # Calculate average duration per regime
    regime_changes = regimes != regimes.shift()
    regime_ids = regime_changes.cumsum()
    regime_durations = regimes.groupby(regime_ids).size()

    print(f"\n   Average regime duration:")
    for regime in ['trending', 'mean_reverting', 'choppy']:
        regime_mask = regimes[regime_ids.isin(regime_ids[regimes == regime])]
        if len(regime_mask) > 0:
            durations = regimes.groupby(regime_ids[regimes == regime]).size()
            avg_duration = durations.mean()
            print(f"      {regime:15s}: {avg_duration:.1f} bars")

    # Trading insights
    print("\n7. Trading Insights:")
    print("-" * 70)

    trending_stats = stats['trending']
    mean_rev_stats = stats['mean_reverting']
    choppy_stats = stats['choppy']

    print(f"\n   Best performing regime:")
    best_regime = max(stats.items(), key=lambda x: x[1]['sharpe'] if x[1]['count'] > 0 else -999)
    if best_regime[1]['count'] > 0:
        print(f"      {best_regime[0].upper()} (Sharpe: {best_regime[1]['sharpe']:.2f})")

    print(f"\n   Risk considerations:")
    if choppy_stats['percentage'] > 80:
        print(f"      ⚠ High choppy percentage ({choppy_stats['percentage']:.1f}%)")
        print(f"        → Consider reducing position sizes or avoiding trades")
    if trending_stats['count'] > 0:
        print(f"      ✓ Trending opportunities: {trending_stats['percentage']:.1f}% of time")
        print(f"        → Focus trend-following strategies during these periods")
    if mean_rev_stats['count'] > 0:
        print(f"      ✓ Mean-reversion opportunities: {mean_rev_stats['percentage']:.1f}% of time")
        print(f"        → Consider range-bound strategies during these periods")

    # Example usage
    print("\n8. Example: Regime-Adaptive Position Sizing:")
    print("-" * 70)

    base_size = 1.0
    current_regime = regimes.iloc[-1]

    if current_regime == 'trending':
        suggested_size = base_size * 1.5
        rationale = "Strong trend detected, increase position"
    elif current_regime == 'mean_reverting':
        suggested_size = base_size * 1.0
        rationale = "Range-bound market, normal position"
    elif current_regime == 'choppy':
        suggested_size = base_size * 0.5
        rationale = "Choppy conditions, reduce risk"
    else:
        suggested_size = base_size * 0.25
        rationale = "Insufficient data, minimal position"

    print(f"   Current regime:     {current_regime}")
    print(f"   Base position size: {base_size:.2f}")
    print(f"   Suggested size:     {suggested_size:.2f}")
    print(f"   Rationale:          {rationale}")

    # Summary
    print_section("DEMO COMPLETE")
    print(f"""
    ✓ Successfully classified {len(regimes)} bars into market regimes
    ✓ Detected {transitions} regime transitions
    ✓ Identified {trending_stats['count']} trending bars ({trending_stats['percentage']:.1f}%)
    ✓ Identified {mean_rev_stats['count']} mean-reverting bars ({mean_rev_stats['percentage']:.1f}%)
    ✓ Identified {choppy_stats['count']} choppy bars ({choppy_stats['percentage']:.1f}%)

    Next Steps:
    1. Integrate with your backtesting system
    2. Test regime-specific strategies
    3. Optimize regime detection thresholds for your market
    4. Use regime filtering for strategy selection

    See REGIME_DETECTOR_README.md for complete documentation.
    """)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
