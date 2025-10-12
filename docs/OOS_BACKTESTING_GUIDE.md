# Out-of-Sample (OOS) Backtesting Guide

## What is OOS Testing?

Out-of-sample testing validates your optimized strategy parameters on completely new data that was NOT used during the optimization process. This is crucial for:

- **Preventing Overfitting**: Ensures your strategy works on unseen data
- **Real-World Validation**: Tests if optimization results generalize
- **Confidence Building**: Provides evidence before live trading
- **Risk Management**: Identifies if parameters are too fitted to specific market conditions

## Quick Start

### 1. Export Winning Parameters (UI Method)

1. Go to **Metrics Dashboard** in the Streamlit UI
2. Select your optimization study
3. View the best trial's metrics and parameters
4. Click the **"📥 Export Parameters"** button
5. Parameters will be saved to: `oos_parameters/trial_X_params_TIMESTAMP.json`

### 2. Prepare OOS Data

Place your out-of-sample data file in a directory:
```
data/
  ES_5m_jan_2024.csv     # In-sample (used for optimization)
  ES_5m_feb_2024.csv     # Out-of-sample (fresh data for validation)
```

**Important**: OOS data should be:
- Same instrument and timeframe
- Different time period (e.g., next month, next quarter)
- NOT used in any way during optimization

### 3. Run OOS Backtest (Command Line)

```bash
python TopStepB/validation/oos_backtest.py \
  --params oos_parameters/trial_X_params_TIMESTAMP.json \
  --data data/ES_5m_feb_2024.csv \
  --strategy bollinger_squeeze \
  --symbol ES \
  --output oos_results_feb_2024.json
```

### 4. Review Results

The output JSON file contains:

```json
{
  "oos_data_file": "data/ES_5m_feb_2024.csv",
  "oos_data_bars": 2500,
  "oos_date_range": "2024-02-01 to 2024-02-29",
  "parameters_used": { ...winning parameters... },
  "in_sample_metrics": { ...optimization results... },
  "oos_metrics": { ...new backtest results... },
  "comparison": {
    "total_dollar_pnl": {
      "in_sample": 15000.0,
      "oos": 12500.0,
      "change_pct": -16.7
    },
    "win_rate": {
      "in_sample": 65.0,
      "oos": 62.0,
      "change_pct": -4.6
    }
    ...
  }
}
```

## Command Line Options

### Export Parameters

```bash
python TopStepB/validation/oos_backtest.py --export \
  --study "bollinger_squeeze_ES_5m_20251012_150818" \
  --trial 68 \
  --output winning_params.json
```

### Run OOS Backtest

```bash
python TopStepB/validation/oos_backtest.py \
  --params winning_params.json \
  --data data/oos_data.csv \
  --strategy bollinger_squeeze \
  --symbol ES \
  --output oos_results.json
```

**Parameters:**
- `--params`: Path to exported parameters JSON file
- `--data`: Path to OOS data file (CSV or Parquet)
- `--strategy`: Strategy name (default: bollinger_squeeze)
- `--symbol`: Trading symbol (default: ES)
- `--output`: Where to save results (optional)

## Interpreting Results

### Good OOS Performance

- **PnL decline < 20%**: Some degradation is normal
- **Win rate decline < 5%**: Strategy remains effective
- **Profit factor > 1.0**: Still profitable
- **Same general behavior**: Similar trade count, risk profile

### Warning Signs

- **PnL decline > 50%**: Possible overfitting
- **Win rate decline > 10%**: Strategy may not generalize
- **Profit factor < 1.0**: Not profitable OOS
- **Drastically different metrics**: Parameters too fitted

### Example Comparison

**Acceptable Degradation:**
```
Metric              In-Sample    OOS       Change
----------------------------------------------------
Total PnL           $20,000      $16,000   -20%    ✓ Good
Win Rate            68%          64%       -4%     ✓ Good
Profit Factor       2.5          2.1       -16%    ✓ Acceptable
Max Drawdown        $3,000       $3,500    +17%    ✓ Acceptable
```

**Concerning Degradation:**
```
Metric              In-Sample    OOS       Change
----------------------------------------------------
Total PnL           $20,000      $5,000    -75%    ✗ Bad
Win Rate            68%          52%       -16%    ✗ Bad
Profit Factor       2.5          0.8       -68%    ✗ Bad
Max Drawdown        $3,000       $8,000    +167%   ✗ Bad
```

## Best Practices

### 1. Data Splitting

**Recommended:**
```
Training:    60% (Jan-Jun 2024) → Optimization
Validation:  20% (Jul-Aug 2024) → Parameter selection
Test:        20% (Sep-Oct 2024) → Final OOS validation
```

### 2. Multiple OOS Periods

Test on several different time periods:
```bash
# Test on 3 different months
python TopStepB/validation/oos_backtest.py --params params.json --data data/feb_2024.csv
python TopStepB/validation/oos_backtest.py --params params.json --data data/mar_2024.csv
python TopStepB/validation/oos_backtest.py --params params.json --data data/apr_2024.csv
```

### 3. Walk-Forward OOS

For production robustness:
1. Optimize on Month 1
2. Test OOS on Month 2
3. Re-optimize on Months 1-2
4. Test OOS on Month 3
5. Repeat...

### 4. Market Regime Testing

Test across different market conditions:
- Bull markets
- Bear markets
- High volatility periods
- Low volatility periods
- Trending vs. ranging markets

## Automation Script

Create a batch script for regular OOS testing:

```bash
#!/bin/bash
# oos_test_suite.sh

PARAMS="oos_parameters/best_trial_params.json"

echo "Running OOS test suite..."

# Test on multiple periods
for month in feb mar apr may jun; do
    echo "Testing ${month} 2024..."
    python TopStepB/validation/oos_backtest.py \
        --params $PARAMS \
        --data data/ES_5m_${month}_2024.csv \
        --symbol ES \
        --output oos_results_${month}_2024.json
done

echo "OOS testing complete!"
```

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the project root:
```bash
cd C:\Users\salte\ClaudeProjects\TopStepB--ackstester-
python TopStepB/validation/oos_backtest.py ...
```

### Data Format Issues

OOS data must match training data format:
- Same columns (datetime, open, high, low, close, volume)
- Same timeframe
- Clean data (no gaps, valid OHLC)

### Strategy Not Found

Ensure the strategy module exists:
```
TopStepB/strategies/bollinger_squeeze/strategy.py
```

## Advanced Usage

### Custom Starting Equity

Modify the OOS backtest script to use different starting equity:

```python
# In oos_backtest.py, line 67
equity_curve = calculate_trade_equity_curve(trade_pnls, starting_equity=100000.0)
```

### Different Account Types

```bash
python TopStepB/validation/oos_backtest.py \
  --params params.json \
  --data data/oos.csv \
  --symbol ES \
  # Add custom account config here
```

### Micro Contracts

For MES testing:
```bash
python TopStepB/validation/oos_backtest.py \
  --params params.json \
  --data data/MES_oos.csv \
  --strategy bollinger_squeeze \
  --symbol MES
```

## FAQ

**Q: How much degradation is acceptable?**
A: Generally, 10-20% decline in PnL is normal. More than 30% suggests overfitting.

**Q: Should I re-optimize after OOS testing?**
A: No! That defeats the purpose. OOS data must remain unseen during optimization.

**Q: How often should I run OOS tests?**
A: After every optimization run, and periodically with new data.

**Q: Can I use the same data for multiple OOS tests?**
A: Once used for OOS, that data is "contaminated" and shouldn't be reused for future OOS tests.

**Q: What if OOS results are much better than in-sample?**
A: Suspicious! You may have data leakage or the OOS period was unusually favorable.

## Support

For issues or questions:
1. Check this guide
2. Review the OOS backtest logs
3. Verify data formats and parameters
4. Test with a simple known-good case first
