# EDGE CASE QUICK REFERENCE CARD
**For Developers - Keep This Handy**

---

## 🎯 CRITICAL EDGE CASES - MUST HANDLE

### 1. Zero/Constant Values
```python
# ATR = 0 (constant prices)
if atr <= 0:
    atr = price * 0.001  # 0.1% minimum

# Standard deviation = 0 (constant values in window)
# ✅ SAFE: Used in multiplication only, not division
# Bands collapse but don't crash

# Volume = 0 (all bars)
# ✅ SAFE: .fillna(1.0) handles NaN from 0/0
```

### 2. NaN Values
```python
# BEFORE any calculation:
clean_data = data.fillna(method='ffill').fillna(method='bfill')
if clean_data.isna().any():
    raise ValueError("NaN values remain after cleaning")

# After calculation (paranoid defense):
if result.isna().any():
    logger.error("NaN propagated through calculation")
```

### 3. Inf Values
```python
# At data loading:
if np.isinf(df[col]).any():
    raise ValueError(f"Inf values in {col}")

# After calculation:
if np.isinf(result).any():
    raise ValueError("Inf produced in calculation")
```

### 4. Division by Zero
```python
# Pattern A: Explicit check
if denominator == 0:
    return 0.0  # or appropriate default

# Pattern B: Conditional
result = numerator / denominator if denominator != 0 else 0.0

# Pattern C: NaN + fillna
result = (numerator / denominator).fillna(0.0)

# Pattern D: Epsilon guard
result = numerator / max(denominator, 1e-10)
```

---

## 📊 DIVISION SAFETY PATTERNS

### ✅ SAFE Examples
```python
# Trading metrics
profit_factor = gross_profit / gross_loss if gross_loss > 0 else 5.0

# Sharpe ratio
sharpe = mean_return / std_return if std_return > 0 else 0.0

# Win rate
win_rate = wins / total_trades if total_trades > 0 else 0.0

# Linear regression
slope = numerator / denom if denom != 0 else 0.0

# Normalization
normalized = (value - min_val) / (max_val - min_val) if max_val != min_val else 0.5
```

### ❌ UNSAFE Example
```python
# DANGER: No check
ticks = price_movement / tick_size  # What if tick_size = 0?

# FIX:
assert tick_size > 0, "Invalid tick_size"
ticks = price_movement / tick_size
```

---

## 🔢 NUMERICAL SAFETY PATTERNS

### Square Root
```python
# Only sqrt of non-negative values
std = np.sqrt(variance) if variance >= 0 else 0.0

# Better: Use max to ensure positive
std = np.sqrt(max(variance, 0.0))

# ✅ ALWAYS SAFE: sqrt of squared values
downside_std = np.sqrt(np.mean(np.square(negative_returns)))
```

### Exponential (Overflow Risk)
```python
# Clip input to safe range
safe_input = np.clip(value, -10, 10)
result = np.exp(safe_input)

# Or use max/min
safe_input = max(-10, min(10, value))
result = np.exp(safe_input)
```

### Logarithm
```python
# Ensure positive input
if value <= 0:
    return float('-inf')  # or raise error
result = np.log(value)

# Or use epsilon
result = np.log(max(value, 1e-10))
```

---

## 📅 DATA VALIDATION CHECKLIST

### At Data Loading
```python
def validate_data(df: pd.DataFrame):
    # 1. Check for NaN
    assert not df.isna().any().any(), "NaN values present"

    # 2. Check for Inf
    assert not np.isinf(df.select_dtypes(include=[np.number])).any().any(), "Inf values present"

    # 3. Check for duplicates
    assert not df.index.duplicated().any(), "Duplicate timestamps"

    # 4. Check for sorting
    assert df.index.is_monotonic_increasing, "Data not sorted"

    # 5. Check for positive prices
    for col in ['open', 'high', 'low', 'close']:
        assert (df[col] > 0).all(), f"Non-positive prices in {col}"

    # 6. Check for valid OHLC relationships
    assert (df['high'] >= df['low']).all(), "High < Low detected"
    assert (df['high'] >= df['close']).all(), "High < Close detected"
    assert (df['low'] <= df['close']).all(), "Low > Close detected"
```

---

## 🎲 SPECIAL VALUE RETURNS

### Zero Trades
```python
return {
    'total_return': 0.0,
    'sharpe_ratio': 0.0,
    'sortino_ratio': 0.0,
    'profit_factor': 0.0,  # or 0.1 to avoid log issues
    'win_rate': 0.0,
    'total_trades': 0
}
```

### All Winning Trades
```python
profit_factor = 5.0  # Bounded high value
```

### All Losing Trades
```python
profit_factor = 0.1  # Bounded low value (avoid 0)
```

### Invalid Calculation
```python
# Return -inf for optimization
return float('-inf')

# Or return None for filtering
return None
```

---

## 🧪 TESTING EDGE CASES

### Create Test Data
```python
# Constant prices (no volatility)
constant_data = pd.DataFrame({
    'close': [100.0] * 1000,
    'high': [100.0] * 1000,
    'low': [100.0] * 1000,
    'open': [100.0] * 1000
})

# With NaN
nan_data = data.copy()
nan_data['close'].iloc[50] = np.nan

# With Inf
inf_data = data.copy()
inf_data['close'].iloc[50] = np.inf

# Zero volume
zero_vol_data = data.copy()
zero_vol_data['volume'] = 0

# Duplicate timestamps
dup_data = pd.concat([data, data.iloc[[0]]])

# Unsorted
unsorted_data = data.sample(frac=1.0)
```

### Quick Test Function
```python
def test_edge_case(data, expected_behavior):
    """
    expected_behavior: 'error', 'zero_trades', 'normal'
    """
    try:
        result = run_strategy(data)
        if expected_behavior == 'error':
            assert False, "Should have raised error"
        elif expected_behavior == 'zero_trades':
            assert result['total_trades'] == 0
        return "PASS"
    except Exception as e:
        if expected_behavior == 'error':
            return f"PASS: {type(e).__name__}"
        return f"FAIL: {e}"
```

---

## 🔍 DEBUGGING EDGE CASES

### Finding NaN Source
```python
# Check each step
print(f"Input NaN count: {data.isna().sum()}")
result1 = step1(data)
print(f"After step1 NaN: {result1.isna().sum()}")
result2 = step2(result1)
print(f"After step2 NaN: {result2.isna().sum()}")
```

### Finding Inf Source
```python
# Check each calculation
print(f"Max value: {result.max()}")
if np.isinf(result).any():
    inf_indices = np.where(np.isinf(result))[0]
    print(f"Inf at indices: {inf_indices[:10]}")
```

### Finding Division by Zero
```python
# Add assertions before divisions
assert denominator != 0, f"Zero denominator at {location}"
result = numerator / denominator
```

---

## 📝 CODE REVIEW CHECKLIST

When reviewing code, check for:

- [ ] All divisions have zero checks
- [ ] All sqrt inputs are non-negative
- [ ] All log inputs are positive
- [ ] All exp inputs are bounded
- [ ] NaN handling after rolling/EMA
- [ ] Inf handling after calculations
- [ ] Data validation at entry points
- [ ] Meaningful defaults for edge cases
- [ ] Test cases for boundary conditions

---

## 🚀 PRODUCTION SAFETY

### Before Deployment
```python
# Add comprehensive logging
logger.info(f"Input data shape: {data.shape}")
logger.info(f"Date range: {data.index[0]} to {data.index[-1]}")
logger.info(f"Price range: {data['close'].min():.2f} to {data['close'].max():.2f}")

# Add data quality checks
validate_data(data)

# Add result validation
assert result['total_trades'] >= 0, "Negative trade count"
assert not np.isnan(result['sharpe_ratio']), "NaN Sharpe ratio"
assert not np.isinf(result['profit_factor']), "Inf profit factor"
```

---

**Remember:** Edge cases are not exceptions - they WILL happen in production!
**Defense:** Validate inputs, check denominators, handle special values, test edge cases.

**Generated:** 2025-10-12
**Source:** EDGE_CASE_ANALYSIS_REPORT.md
