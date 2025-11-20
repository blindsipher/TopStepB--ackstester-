# Regime Detection Integration Guide

## Overview

The regime detection system allows you to filter your data to only include specific market regimes before running optimization. This helps you:

- **Improve optimization quality** - Train on data that matches your strategy's intended market conditions
- **Reduce bad trials** - Eliminate trials on unsuitable market conditions
- **Focus on regime-specific strategies** - Build trend-following systems for trending markets only, or mean-reversion systems for ranging markets

## Quick Start

### Enable Regime Filtering (CLI)

```bash
python -m TopStepB.main_runner \
  --strategy=TrendFollower \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --use-regime-filter \
  --regime-types=trending \
  --regime-lookback=100 \
  --min-regime-bars=200
```

### Key CLI Flags

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--use-regime-filter` | Enable regime filtering | False | `--use-regime-filter` |
| `--regime-types` | Comma-separated regimes to include | trending | `--regime-types=trending,mean_reverting` |
| `--regime-lookback` | Bars needed for regime detection | 100 | `--regime-lookback=150` |
| `--min-regime-bars` | Minimum bars required after filtering | 200 | `--min-regime-bars=500` |

## Regime Types

### 1. Trending
**Characteristics:**
- High ADX (>25)
- Strong directional momentum
- Clear price trends

**Best for:**
- Trend-following strategies
- Breakout systems
- Momentum strategies

**Example:**
```bash
--use-regime-filter --regime-types=trending
```

### 2. Mean Reverting
**Characteristics:**
- Low ADX (<20)
- High volatility
- Range-bound price action

**Best for:**
- Mean-reversion strategies
- Counter-trend systems
- Range-trading strategies

**Example:**
```bash
--use-regime-filter --regime-types=mean_reverting
```

### 3. Choppy
**Characteristics:**
- Low ADX (<20)
- Low volatility
- No clear direction
- Sideways movement

**Best for:**
- Testing robustness
- Identifying strategies that work in all conditions
- Usually avoided for optimization

**Example:**
```bash
--use-regime-filter --regime-types=choppy
```

### Multiple Regimes

You can combine multiple regime types:

```bash
--regime-types=trending,mean_reverting
```

This filters data to include ONLY bars in either trending OR mean-reverting regimes, excluding choppy markets.

## Configuration Parameters

### Regime Lookback Period

Controls how many bars are needed before regime classification begins.

```bash
--regime-lookback=100  # Default: 100 bars
```

- **Shorter (50-75)**: Faster regime detection, more responsive to changes, may be noisier
- **Default (100)**: Balanced approach, good for most timeframes
- **Longer (150-200)**: More stable regime classification, slower to adapt

**Recommendation by Timeframe:**
- 1-minute: 100-150 bars
- 5-minute: 100 bars (default)
- 15-minute: 75-100 bars
- 1-hour: 50-75 bars
- Daily: 30-50 bars

### Minimum Regime Bars

Ensures you have enough data after filtering for meaningful optimization.

```bash
--min-regime-bars=200  # Default: 200 bars
```

**Guidelines:**
- **Minimum recommended**: 200 bars (bare minimum for basic backtesting)
- **Conservative**: 500-1000 bars (better statistical significance)
- **Robust**: 2000+ bars (high confidence in results)

**What happens if insufficient bars?**
Pipeline will fail with a clear error message:
```
Only 150 bars found in regimes ['trending'].
Required minimum: 200 bars.
Try different regime types, reduce --min-regime-bars, or disable regime filtering.
```

## Integration Flow

### Pipeline Execution Order

```
1. Data Loading
   ↓
2. Regime Detection (if --use-regime-filter)
   ├─ Detect regimes for all bars
   ├─ Filter to specified regime types
   ├─ Validate minimum bars requirement
   └─ Update state.full_data with filtered data
   ↓
3. Strategy Discovery
   ↓
4. Trading Configuration
   ↓
5. Data Splitting (on filtered data)
   ↓
6. Optimization (on regime-filtered splits)
   ↓
7. Deployment
   ↓
8. Validation
   ↓
9. Analytics & Packaging
```

**Key Point**: Regime filtering happens BEFORE data splitting, so your train/validation/test splits all contain only the selected regime types.

## Performance Characteristics

### Expected Performance

- **Target**: <1 second for 5000 bars
- **Typical**: 0.2-0.5 seconds for 5000 bars
- **Acceptable**: <2 seconds for 10000 bars

### Performance Tuning

The regime detector uses Numba JIT compilation for maximum speed:
- First run may be slower (JIT compilation)
- Subsequent runs are very fast (compiled code cached)
- Optimized for large datasets (10K+ bars)

### Memory Impact

- **Minimal overhead**: Regime detection adds one additional column (regime labels)
- **Filtering reduces memory**: Filtered data is smaller than original
- **No data duplication**: Operates in-place where possible

## Production Usage

### Headless Linux Server

1. **Install dependencies:**
```bash
pip install -r requirements-headless.txt
```

2. **Run with regime filtering:**
```bash
python -m TopStepB.main_runner \
  --strategy=YourStrategy \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --data-file=/path/to/your/data.parquet \
  --use-regime-filter \
  --regime-types=trending \
  --max-trials=100
```

3. **Verify regime filtering:**
Check logs for:
```
INFO: Applying regime filter: ['trending'] (lookback=100)
INFO: Regime filtering completed in 0.234s: 5000 bars → 2847 bars (56.9%)
```

### Recommended Workflow

1. **Start with default settings:**
   - Use default lookback (100)
   - Use default min_regime_bars (200)
   - Filter to single regime type

2. **Analyze results:**
   - Check how many bars remain after filtering
   - Verify optimization still has enough data
   - Review regime distribution in logs

3. **Tune parameters:**
   - Adjust regime_types based on strategy
   - Increase min_regime_bars for more data
   - Adjust lookback for different timeframes

4. **Run production optimization:**
   - Use conservative min_regime_bars (500+)
   - Enable multiple regime types if needed
   - Monitor performance metrics

## Troubleshooting

### Error: "Only X bars found, need at least Y"

**Problem**: Not enough bars in selected regime(s).

**Solutions:**
1. Reduce `--min-regime-bars`:
   ```bash
   --min-regime-bars=150
   ```

2. Add more regime types:
   ```bash
   --regime-types=trending,mean_reverting
   ```

3. Use more data:
   ```bash
   --data-file=/path/to/larger/dataset.parquet
   ```

4. Disable regime filtering:
   ```bash
   # Remove --use-regime-filter flag
   ```

### Warning: "Regime detection took X seconds"

**Problem**: Performance slower than target (<1s).

**Solutions:**
1. Check data size (may be normal for 10K+ bars)
2. Ensure Numba is installed correctly:
   ```bash
   pip install numba>=0.58
   ```
3. Reduce regime_lookback if very large:
   ```bash
   --regime-lookback=75
   ```

### Issue: Too much data filtered out

**Problem**: Filtering removes 90%+ of data.

**Analysis:**
- This may be expected for some regimes (e.g., strong trends are rare)
- Check regime distribution in logs

**Solutions:**
1. Use multiple regime types:
   ```bash
   --regime-types=trending,mean_reverting
   ```

2. Adjust regime detection thresholds (advanced):
   - Modify `TopStepB/data/regime_detector.py`
   - Customize `thresholds` parameter in `classify_regime()`

3. Use more historical data

## Advanced Usage

### Custom Regime Thresholds

For advanced users, you can modify regime classification thresholds in `regime_detector.py`:

```python
thresholds = {
    'adx_high': 25.0,      # Increase to require stronger trends
    'adx_low': 20.0,       # Decrease to classify more as trending
    'volatility_high': 2.0,
    'volatility_low': 1.0,
    'momentum_threshold': 2.0,
    'compression_high': 1.2,
    'compression_low': 0.8
}
```

### Programmatic Usage

```python
from TopStepB.data.regime_detector import detect_regime, filter_by_regime

# Detect regimes
regimes = detect_regime(data, lookback=100)

# Filter to trending markets only
trending_data = filter_by_regime(data, 'trending', lookback=100)

# Get regime statistics
from TopStepB.data.regime_detector import calculate_regime_statistics
stats = calculate_regime_statistics(data, regimes)
```

## Testing

### Quick Test

```bash
# Test with synthetic data (no --data-file)
python -m TopStepB.main_runner \
  --strategy=SimpleMovingAverageCrossover \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --synthetic-bars=5000 \
  --use-regime-filter \
  --regime-types=trending \
  --max-trials=10
```

### Benchmark Test

```bash
# Run 50-trial benchmark
python -m TopStepB.main_runner \
  --strategy=SimpleMovingAverageCrossover \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --data-file=path/to/data.parquet \
  --use-regime-filter \
  --regime-types=trending \
  --max-trials=50 \
  --max-workers=4
```

## Examples

### Example 1: Trend-Following Strategy

Optimize a trend-following strategy on trending markets only:

```bash
python -m TopStepB.main_runner \
  --strategy=TrendFollower \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --data-file=data/ES_5m_2024.parquet \
  --use-regime-filter \
  --regime-types=trending \
  --regime-lookback=100 \
  --min-regime-bars=500 \
  --max-trials=100 \
  --max-workers=4
```

### Example 2: Mean-Reversion Strategy

Optimize a mean-reversion strategy on ranging markets:

```bash
python -m TopStepB.main_runner \
  --strategy=MeanReversion \
  --symbol=NQ \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --data-file=data/NQ_5m_2024.parquet \
  --use-regime-filter \
  --regime-types=mean_reverting \
  --regime-lookback=100 \
  --min-regime-bars=500 \
  --max-trials=100
```

### Example 3: Multi-Regime Strategy

Test a strategy across both trending and mean-reverting markets:

```bash
python -m TopStepB.main_runner \
  --strategy=AdaptiveStrategy \
  --symbol=ES \
  --timeframe=5m \
  --account-type=topstep_50k \
  --slippage=0.5 \
  --commission=2.50 \
  --contracts-per-trade=1 \
  --split-type=chronological \
  --data-file=data/ES_5m_2024.parquet \
  --use-regime-filter \
  --regime-types=trending,mean_reverting \
  --regime-lookback=100 \
  --min-regime-bars=1000 \
  --max-trials=150
```

## Performance Benchmarks

### Expected Results (5000-bar dataset, Python 3.11.9, Linux)

| Component | Time (seconds) | Notes |
|-----------|---------------|-------|
| Regime Detection | 0.2-0.5 | Numba JIT compiled |
| Data Filtering | 0.05-0.1 | Pandas boolean indexing |
| **Total Overhead** | **<1.0** | **Target met** |

### Scaling Characteristics

| Dataset Size | Expected Time | Notes |
|--------------|--------------|-------|
| 1,000 bars | <0.1s | Very fast |
| 5,000 bars | 0.2-0.5s | Target performance |
| 10,000 bars | 0.5-1.5s | Still fast |
| 50,000 bars | 2-5s | Acceptable |
| 100,000+ bars | 5-15s | Consider chunking |

## Best Practices

### 1. Strategy-Regime Alignment
- **Trend-following**: Use `--regime-types=trending`
- **Mean-reversion**: Use `--regime-types=mean_reverting`
- **Adaptive**: Use `--regime-types=trending,mean_reverting`

### 2. Data Requirements
- Minimum 200 bars after filtering (absolute minimum)
- Recommended 500-1000 bars (good statistical power)
- Ideal 2000+ bars (high confidence)

### 3. Performance Optimization
- Use Parquet files (faster I/O than CSV)
- Appropriate regime_lookback for your timeframe
- Monitor regime filtering percentage in logs

### 4. Testing Workflow
1. Start with small trial count (10-20) to validate
2. Check regime filtering statistics in logs
3. Adjust parameters if needed
4. Scale to full optimization (100+ trials)

### 5. Production Deployment
- Use `requirements-headless.txt` for servers
- Set conservative `--min-regime-bars` (500+)
- Monitor performance metrics
- Log regime distribution for analysis

## FAQ

**Q: Does regime filtering guarantee better results?**
A: Not guaranteed, but it helps focus optimization on relevant market conditions. Test both with and without filtering.

**Q: Can I use regime filtering with walk-forward splits?**
A: Yes! Regime filtering happens before splitting, so it works with both chronological and walk-forward splits.

**Q: How do I know which regime type to use?**
A: Match the regime to your strategy type:
- Trend-following → trending
- Mean-reversion → mean_reverting
- Adaptive → multiple regimes or no filtering

**Q: Does regime filtering slow down optimization?**
A: No. Filtering actually speeds up optimization because there's less data to process.

**Q: What if my data has no trending periods?**
A: You'll get an error about insufficient bars. Try different regime types or use more historical data.

**Q: Can I modify regime detection thresholds?**
A: Yes, but it's advanced. Modify `TopStepB/data/regime_detector.py` directly.

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Review this guide's troubleshooting section
3. Verify your data has sufficient bars
4. Test with smaller parameter values first

## Version History

- **v1.0** (2025-11-20): Initial release
  - CLI integration
  - Three regime types (trending, mean_reverting, choppy)
  - Performance optimized (<1s for 5000 bars)
  - Headless Linux compatibility
