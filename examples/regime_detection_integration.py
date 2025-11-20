"""
Market Regime Detection Integration Examples
============================================

Demonstrates how to integrate regime detection with the existing data pipeline:

1. Basic regime detection on loaded data
2. Regime-aware data splitting for backtesting
3. Regime filtering for strategy-specific testing
4. Regime statistics and analysis
5. Integration with walk-forward optimization

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
import matplotlib.pyplot as plt

from TopStepB.data.data_loader import load_data_file, create_synthetic_data
from TopStepB.data.regime_detector import (
    detect_regime,
    detect_regime_with_indicators,
    filter_by_regime,
    calculate_regime_statistics,
    add_regime_to_data
)
from TopStepB.data.data_splitter import chronological_split


# ============================================================================
# Example 1: Basic Regime Detection
# ============================================================================

def example_basic_regime_detection():
    """Basic example of regime detection on synthetic data."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Regime Detection")
    print("="*70)

    # Load or create data
    print("\n1. Loading data...")
    data = create_synthetic_data(bars=2000, symbol="ES", timeframe="15min")
    print(f"   Loaded {len(data)} bars of ES futures data")

    # Detect regimes
    print("\n2. Detecting market regimes...")
    regimes = detect_regime(data, lookback=100)

    # Display results
    print("\n3. Regime Distribution:")
    regime_counts = regimes.value_counts()
    for regime, count in regime_counts.items():
        pct = count / len(regimes) * 100
        print(f"   {regime:15s}: {count:4d} bars ({pct:5.1f}%)")

    # Show recent regimes
    print("\n4. Recent regime classifications:")
    recent = pd.DataFrame({
        'datetime': data['datetime'].tail(10),
        'close': data['close'].tail(10),
        'regime': regimes.tail(10)
    })
    print(recent.to_string(index=False))

    return data, regimes


# ============================================================================
# Example 2: Detailed Regime Analysis with Indicators
# ============================================================================

def example_detailed_regime_analysis():
    """Show regime detection with all underlying indicators."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Detailed Regime Analysis")
    print("="*70)

    # Create data
    print("\n1. Creating synthetic data...")
    data = create_synthetic_data(bars=1000, symbol="NQ", timeframe="5min")

    # Detect regimes with indicators
    print("\n2. Calculating regimes and indicators...")
    detailed = detect_regime_with_indicators(data, lookback=100)

    # Display summary statistics
    print("\n3. Indicator Summary by Regime:")
    print("-" * 70)

    for regime in ['trending', 'mean_reverting', 'choppy']:
        regime_data = detailed[detailed['regime'] == regime]
        if len(regime_data) > 0:
            print(f"\n{regime.upper()}:")
            print(f"  ADX:               {regime_data['adx'].mean():.2f} (avg)")
            print(f"  Volatility:        {regime_data['volatility'].mean():.2f} (avg)")
            print(f"  Momentum:          {regime_data['momentum'].mean():.2f} (avg)")
            print(f"  Range Compression: {regime_data['range_compression'].mean():.2f} (avg)")

    # Show sample of detailed data
    print("\n4. Sample of detailed indicators (last 5 bars):")
    print(detailed[['regime', 'adx', 'volatility', 'momentum', 'range_compression']].tail().to_string())

    return detailed


# ============================================================================
# Example 3: Regime-Specific Strategy Testing
# ============================================================================

def example_regime_specific_testing():
    """Filter data by regime for strategy-specific backtesting."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Regime-Specific Strategy Testing")
    print("="*70)

    # Create data
    print("\n1. Loading data...")
    data = create_synthetic_data(bars=2000, symbol="ES", timeframe="15min")

    # Test different strategies on different regimes
    print("\n2. Filtering data by regime...")

    regimes = ['trending', 'mean_reverting', 'choppy']
    for regime in regimes:
        filtered_data = filter_by_regime(data, regime, lookback=100)
        print(f"\n   {regime.upper()} regime:")
        print(f"   - Total bars: {len(filtered_data)}")
        print(f"   - Date range: {filtered_data['datetime'].min()} to {filtered_data['datetime'].max()}")

        if len(filtered_data) > 0:
            returns = filtered_data['close'].pct_change()
            print(f"   - Avg return: {returns.mean()*100:.4f}%")
            print(f"   - Volatility: {returns.std()*100:.4f}%")

    return data


# ============================================================================
# Example 4: Regime Statistics and Analysis
# ============================================================================

def example_regime_statistics():
    """Calculate comprehensive statistics for each regime."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Regime Statistics and Analysis")
    print("="*70)

    # Create data
    print("\n1. Creating synthetic data...")
    data = create_synthetic_data(bars=3000, symbol="ES", timeframe="15min")

    # Detect regimes
    print("\n2. Detecting regimes...")
    regimes = detect_regime(data, lookback=100)

    # Calculate statistics
    print("\n3. Calculating regime statistics...")
    stats = calculate_regime_statistics(data, regimes)

    # Display statistics
    print("\n4. Comprehensive Regime Statistics:")
    print("="*70)

    for regime, metrics in stats.items():
        print(f"\n{regime.upper()}:")
        print(f"  Bars:          {metrics['count']:5d} ({metrics['percentage']:5.1f}%)")
        print(f"  Mean Return:   {metrics['mean_return']:7.4f}%")
        print(f"  Volatility:    {metrics['volatility']:7.4f}%")
        print(f"  Sharpe Ratio:  {metrics['sharpe']:7.2f}")
        print(f"  Max Drawdown:  {metrics['max_drawdown']:7.2f}%")

    return stats


# ============================================================================
# Example 5: Integration with Data Splitter
# ============================================================================

def example_regime_aware_splitting():
    """Demonstrate regime-aware data splitting for backtesting."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Regime-Aware Data Splitting")
    print("="*70)

    # Create data
    print("\n1. Creating synthetic data...")
    data = create_synthetic_data(bars=3000, symbol="ES", timeframe="15min")

    # Add regime to data
    print("\n2. Adding regime labels to data...")
    data_with_regime = add_regime_to_data(data, lookback=100)

    # Split data
    print("\n3. Performing chronological 3-way split...")
    split = chronological_split(data_with_regime, ratios=(0.6, 0.2, 0.2), gap_days=1)

    print(f"\n4. Split Summary:")
    print(f"   Train:      {split.train_bars} bars")
    print(f"   Validation: {split.validation_bars} bars")
    print(f"   Test:       {split.test_bars} bars")

    # Analyze regime distribution in each split
    print("\n5. Regime Distribution by Split:")

    for split_name, split_data in [('Train', split.train),
                                    ('Validation', split.validation),
                                    ('Test', split.test)]:
        print(f"\n   {split_name}:")
        regime_counts = split_data['regime'].value_counts()
        for regime, count in regime_counts.items():
            pct = count / len(split_data) * 100
            print(f"      {regime:15s}: {count:4d} bars ({pct:5.1f}%)")

    return split


# ============================================================================
# Example 6: Regime Transition Analysis
# ============================================================================

def example_regime_transitions():
    """Analyze regime transitions and their characteristics."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Regime Transition Analysis")
    print("="*70)

    # Create data
    print("\n1. Creating synthetic data...")
    data = create_synthetic_data(bars=2000, symbol="NQ", timeframe="15min")

    # Detect regimes
    print("\n2. Detecting regimes...")
    regimes = detect_regime(data, lookback=100)

    # Find transitions
    print("\n3. Analyzing regime transitions...")
    transitions = regimes != regimes.shift()
    transition_points = data[transitions].copy()
    transition_points['from_regime'] = regimes.shift()[transitions]
    transition_points['to_regime'] = regimes[transitions]

    # Remove first transition (from NaN)
    transition_points = transition_points[1:]

    print(f"\n4. Found {len(transition_points)} regime transitions")

    # Count transition types
    print("\n5. Transition Types:")
    transition_types = transition_points.groupby(['from_regime', 'to_regime']).size()
    for (from_regime, to_regime), count in transition_types.items():
        if from_regime != 'unknown' and to_regime != 'unknown':
            print(f"   {from_regime:15s} -> {to_regime:15s}: {count:3d} times")

    # Show sample transitions
    print("\n6. Sample Transitions (first 5):")
    sample_cols = ['datetime', 'close', 'from_regime', 'to_regime']
    print(transition_points[sample_cols].head().to_string(index=False))

    return transition_points


# ============================================================================
# Example 7: Custom Threshold Configuration
# ============================================================================

def example_custom_thresholds():
    """Demonstrate custom threshold configuration for regime detection."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Threshold Configuration")
    print("="*70)

    # Create data
    print("\n1. Creating synthetic data...")
    data = create_synthetic_data(bars=1000, symbol="ES", timeframe="15min")

    # Default thresholds
    print("\n2. Default thresholds:")
    regimes_default = detect_regime(data, lookback=100)
    default_counts = regimes_default.value_counts()
    print("   Regime distribution:")
    for regime, count in default_counts.items():
        pct = count / len(regimes_default) * 100
        print(f"      {regime:15s}: {count:4d} bars ({pct:5.1f}%)")

    # Conservative thresholds (stricter trending classification)
    print("\n3. Conservative thresholds (stricter):")
    conservative_thresholds = {
        'adx_high': 30.0,  # Higher ADX required for trending
        'adx_low': 25.0,
        'volatility_high': 2.5,
        'volatility_low': 1.0,
        'momentum_threshold': 3.0,  # Higher momentum required
        'compression_high': 1.3,
        'compression_low': 0.7
    }
    regimes_conservative = detect_regime(data, lookback=100, thresholds=conservative_thresholds)
    conservative_counts = regimes_conservative.value_counts()
    print("   Regime distribution:")
    for regime, count in conservative_counts.items():
        pct = count / len(regimes_conservative) * 100
        print(f"      {regime:15s}: {count:4d} bars ({pct:5.1f}%)")

    # Aggressive thresholds (easier trending classification)
    print("\n4. Aggressive thresholds (more lenient):")
    aggressive_thresholds = {
        'adx_high': 20.0,  # Lower ADX required for trending
        'adx_low': 15.0,
        'volatility_high': 1.5,
        'volatility_low': 0.5,
        'momentum_threshold': 1.0,  # Lower momentum required
        'compression_high': 1.1,
        'compression_low': 0.9
    }
    regimes_aggressive = detect_regime(data, lookback=100, thresholds=aggressive_thresholds)
    aggressive_counts = regimes_aggressive.value_counts()
    print("   Regime distribution:")
    for regime, count in aggressive_counts.items():
        pct = count / len(regimes_aggressive) * 100
        print(f"      {regime:15s}: {count:4d} bars ({pct:5.1f}%)")

    return {
        'default': regimes_default,
        'conservative': regimes_conservative,
        'aggressive': regimes_aggressive
    }


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all integration examples."""
    print("\n" + "="*70)
    print("MARKET REGIME DETECTION - INTEGRATION EXAMPLES")
    print("="*70)

    try:
        # Run examples
        print("\nRunning integration examples...")

        example_basic_regime_detection()
        example_detailed_regime_analysis()
        example_regime_specific_testing()
        example_regime_statistics()
        example_regime_aware_splitting()
        example_regime_transitions()
        example_custom_thresholds()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*70)

    except Exception as e:
        print(f"\n[ERROR] Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
