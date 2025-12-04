# Metric Naming Analysis: total_return_pct vs total_return_percentage

## Executive Summary

**CRITICAL FINDING:** The codebase has inconsistent metric naming with two different names used interchangeably:
- `total_return_percentage` - Used as the PRIMARY metric name
- `total_return_pct` - Used as an ALIAS

**RECOMMENDATION:** Standardize on `total_return_percentage` throughout the codebase. The `total_return_pct` alias should be deprecated with clear deprecation warnings.

---

## Complete Metric Reference Locations

### PRODUCERS (Where metrics are CREATED/RETURNED)

#### 1. **VectorBT Engine** - `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_engine.py`

**Lines 236-237: Zero-trade metrics dictionary**
```python
'total_return_percentage': 0.0,
'total_return_pct': 0.0,
```
- **Context:** `_get_zero_trade_metrics()` method
- **Role:** Initializes both names with zero values for no-trade scenarios
- **Status:** Both names exist as ALIASES

---

#### 2. **VectorBT Validator** - `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_validator.py`

**Line 163: Composite score metrics returned**
```python
'total_return_pct': float(stats.get('Total Return [%]', 0)),
```
- **Context:** `get_composite_score_metrics()` method
- **Role:** Returns metrics in scorers.py format
- **Status:** Uses only `total_return_pct` (INCONSISTENT with vectorbt_engine.py)
- **Issue:** Does NOT return `total_return_percentage`

**Lines 119-120: Internal fallback calculation**
```python
total_return_pct = stats.get('Total Return [%]', 0)
total_pnl = (total_return_pct / 100) * initial_cash
```
- **Context:** `get_composite_score_metrics()` method, line 119 in exception handler
- **Role:** Local variable used to calculate daily PnL fallback
- **Status:** Used internally only

---

#### 3. **Objective Factory** - `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/objective.py`

**Lines 1054, 2163: Loop-based backtest metrics**
```python
total_return_percentage = (total_dollar_pnl / starting_equity) * 100  # REPORTING ONLY
```
- **Context:** `_run_loop_based_backtest()` method
- **Role:** Calculates percentage return from dollar PnL
- **Status:** Local variable, NOT returned directly in dict

**Lines 1112, 2221: Metrics dictionary returned from loop-based backtest**
```python
'total_return': total_return_percentage,
```
- **Context:** Stored as key `'total_return'` (NOT as `'total_return_percentage'`)
- **Role:** Primary return value field
- **Status:** Uses calculated `total_return_percentage` but stores under different key

**Lines 1120, 2229: Net profit alias**
```python
'net_profit': total_return_percentage,
```
- **Context:** Duplicate reference to same percentage value
- **Role:** Provides alternative name for same metric

**Lines 1126, 2235: Legacy compatibility field**
```python
'pnl': total_return_percentage,  # Legacy compatibility (REPORTING ONLY)
```
- **Context:** Another alias for reporting
- **Role:** Backward compatibility
- **Status:** Marked as "Legacy" and "REPORTING ONLY"

---

### CONSUMERS (Where metrics are READ/USED)

#### 1. **Objective Factory - VectorBT Metrics Mapping** - `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/objective.py`

**Lines 871, 879, 885, 1980, 1988, 1994 (appears twice - duplicate code sections)**

In `_map_vectorbt_metrics()` method:
```python
Line 871:  'total_return': vbt_metrics.get('total_return_percentage', 0.0),
Line 879:  'net_profit': vbt_metrics.get('total_return_percentage', 0.0),
Line 885:  'pnl': vbt_metrics.get('total_return_percentage', 0.0),
```

And identically in a second instance:
```python
Line 1980: 'total_return': vbt_metrics.get('total_return_percentage', 0.0),
Line 1988: 'net_profit': vbt_metrics.get('total_return_percentage', 0.0),
Line 1994: 'pnl': vbt_metrics.get('total_return_percentage', 0.0),
```

- **Role:** CONSUMER - reads `total_return_percentage` from VectorBT metrics
- **Status:** Explicitly looks for `'total_return_percentage'` as key
- **Finding:** Does NOT look for `'total_return_pct'` - would fail if vectorbt_validator returned only `total_return_pct`

---

#### 2. **Integration Tests** - `/home/jake/Desktop/TopStepB--ackstester-/tests/test_integration_simple.py`

**Line 237: Required metrics validation**
```python
required_metrics = [
    'total_dollar_pnl', 'total_return_percentage', 'sharpe_ratio',
    ...
]
```

- **Role:** CONSUMER - validates that metrics dict contains `'total_return_percentage'`
- **Status:** Expects only `'total_return_percentage'` (NOT `total_return_pct`)
- **Finding:** Test would PASS if `total_return_percentage` exists, regardless of `total_return_pct`

---

## Data Flow Analysis

```
VectorBT Engine (Producer)
    |
    +-- Returns: 'total_return_percentage' + 'total_return_pct'
    |
    V
Objective Factory._map_vectorbt_metrics() (Consumer)
    |
    +-- READS: 'total_return_percentage' (lines 871, 879, 885)
    +-- IGNORES: 'total_return_pct'
    |
    +-- WRITES: 'total_return', 'net_profit', 'pnl'
    |
    V
Composite Scorer (Consumer)
    |
    +-- READS: 'total_return', 'net_profit', 'pnl'
    +-- NEVER directly reads 'total_return_percentage'
    |
    V
Integration Tests (Consumer)
    |
    +-- VALIDATES: 'total_return_percentage' exists in returned dict
    |
    V
Final Output/Reports
```

---

## Broken Integration: CRITICAL ISSUE

**VectorBT Validator has a CRITICAL INCONSISTENCY:**

```
VectorBT Validator.get_composite_score_metrics() returns:
    'total_return_pct': float(stats.get('Total Return [%]', 0))

BUT DOES NOT return:
    'total_return_percentage'
```

**This breaks the contract with `Objective._map_vectorbt_metrics()` which expects `'total_return_percentage'`**

The mapping function will get `None` and default to 0.0:
```python
'total_return': vbt_metrics.get('total_return_percentage', 0.0),  # Gets None -> uses 0.0
```

---

## Metric Name Usage Summary

| Metric Name | Type | Locations | Recommendation |
|---|---|---|---|
| `total_return_percentage` | Variable | objective.py (lines 1054, 2163) | KEEP - this is the calculation variable |
| `'total_return_percentage'` | Dict key | vectorbt_engine.py (lines 236) | PRIMARY - use everywhere |
| `'total_return_pct'` | Dict key | vectorbt_engine.py (line 237), vectorbt_validator.py (line 163) | DEPRECATE - remove/replace |
| `'total_return'` | Dict key | objective.py (1112, 2221, etc.) | KEEP - used in output |
| `'net_profit'` | Dict key | objective.py (1120, 2229) | KEEP - but is alias |
| `'pnl'` | Dict key | objective.py (1126, 2235) | DEPRECATE - marked as "Legacy" |

---

## Problem Areas Identified

### 1. **VectorBT Validator Inconsistency (CRITICAL)**
- File: `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_validator.py`
- Line: 163
- Problem: Returns `'total_return_pct'` instead of `'total_return_percentage'`
- Impact: Breaks contract with objective.py's `_map_vectorbt_metrics()` method
- Fix: Change to `'total_return_percentage'`

### 2. **Duplicate Code Sections in Objective Factory**
- File: `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/objective.py`
- Lines: 869-887 AND 1978-1996 (nearly identical)
- Problem: `_map_vectorbt_metrics()` defined twice with identical logic
- Impact: Maintenance nightmare, inconsistencies will propagate to both
- Fix: Consolidate to single method

### 3. **Undefined Metric in VectorBT Engine**
- File: `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_engine.py`
- Line: 237
- Problem: `'total_return_pct'` is initialized but never populated by the engine
- Impact: Always remains 0.0, serves no purpose
- Fix: Remove the line entirely

### 4. **Test Validation Loose**
- File: `/home/jake/Desktop/TopStepB--ackstester-/tests/test_integration_simple.py`
- Line: 237
- Problem: Validates `'total_return_percentage'` but doesn't catch if it's missing from VectorBT output
- Impact: Tests pass even though VectorBT Validator breaks the contract
- Fix: Add stronger validation that keys actually contain data

---

## Data Flow Issues

### Current (BROKEN) Flow:
```
1. VectorBT Engine returns:
   {
     'total_return_percentage': 0.05,
     'total_return_pct': 0.0,  <-- unused
     ...
   }

2. Objective._map_vectorbt_metrics() reads:
   vbt_metrics.get('total_return_percentage', 0.0)
   # Gets 0.05 correctly

3. BUT VectorBT Validator returns:
   {
     'total_return_pct': 0.05,  <-- wrong key name
     # Missing 'total_return_percentage'
   }

4. Objective._map_vectorbt_metrics() then fails:
   vbt_metrics.get('total_return_percentage', 0.0)
   # Returns 0.0 (default) because key doesn't exist!
```

---

## Recommended Changes (Priority Order)

### PRIORITY 1: CRITICAL FIX
**File:** `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_validator.py`
**Line:** 163
**Change:**
```python
# BEFORE:
'total_return_pct': float(stats.get('Total Return [%]', 0)),

# AFTER:
'total_return_percentage': float(stats.get('Total Return [%]', 0)),
```
**Reason:** Restores contract with objective.py's `_map_vectorbt_metrics()`

### PRIORITY 2: REMOVE UNUSED ALIAS
**File:** `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/vectorbt_engine.py`
**Line:** 237
**Change:**
```python
# BEFORE:
'total_return_percentage': 0.0,
'total_return_pct': 0.0,

# AFTER (just remove line 237):
'total_return_percentage': 0.0,
```
**Reason:** `total_return_pct` is never populated, serves no purpose

### PRIORITY 3: CONSOLIDATE DUPLICATE METHODS
**File:** `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/objective.py`
**Lines:** 869-887 AND 1978-1996
**Action:** Identify why there are two identical `_map_vectorbt_metrics()` implementations and consolidate
**Reason:** Prevent maintenance issues and inconsistencies

### PRIORITY 4: CLEAN UP LEGACY ALIASES
**File:** `/home/jake/Desktop/TopStepB--ackstester-/TopStepB/optimization/objective.py`
**Lines:** 1126, 2235
**Current:**
```python
'pnl': total_return_percentage,  # Legacy compatibility (REPORTING ONLY)
```
**Recommendation:** Add deprecation notice and plan removal in next version

---

## Backward Compatibility Assessment

### Safe to Change:
- `total_return_pct` → `total_return_percentage` in vectorbt_validator.py line 163
  - **Why:** Only internal usage, not exposed to external API

### Safe to Remove:
- Line 237 in vectorbt_engine.py (`'total_return_pct': 0.0`)
  - **Why:** Never populated, never consumed, serves no purpose

### Keep but Deprecate:
- `'pnl'` field in metrics dictionaries
  - **Why:** Currently used by legacy code paths, but marked as deprecated
  - **Action:** Add `DeprecationWarning` when accessed

### Internal Variable (Safe):
- `total_return_percentage` variable in objective.py
  - **Why:** Local variable only, not exposed in API
  - **Status:** Use as-is for clarity

---

## Summary Table: All References

| Location | Line(s) | Type | Current Name | Issue | Fix |
|---|---|---|---|---|---|
| vectorbt_engine.py | 236 | Producer | total_return_percentage | Good | Keep |
| vectorbt_engine.py | 237 | Producer | total_return_pct | Never populated | Remove |
| vectorbt_validator.py | 163 | Producer | total_return_pct | Wrong key name | Change to total_return_percentage |
| objective.py | 1054, 2163 | Calc variable | total_return_percentage | Good | Keep |
| objective.py | 1112, 1120, 1126, 2221, 2229, 2235 | Output dict | total_return, net_profit, pnl | Multiple aliases | Keep, but standardize |
| objective.py | 871, 879, 885, 1980, 1988, 1994 | Consumer | Reads total_return_percentage | Good | Keep |
| test_integration_simple.py | 237 | Validator | Expects total_return_percentage | Good | Keep |

---

## Final Recommendation

**STANDARDIZE ON: `total_return_percentage`**

This metric represents the total return as a percentage of the initial capital.

### Implementation Plan:

1. **Immediate (Critical):**
   - Fix vectorbt_validator.py line 163: return `'total_return_percentage'` instead of `'total_return_pct'`
   - Remove vectorbt_engine.py line 237: `'total_return_pct': 0.0` (dead code)

2. **Short-term (Clean-up):**
   - Investigate and consolidate duplicate methods in objective.py
   - Add docstring clarifications about metric definitions

3. **Medium-term (Deprecation):**
   - Mark `'pnl'` field as deprecated with warnings
   - Plan removal in next major version

4. **Backward Compatibility:**
   - The metric dictionary keys can continue to support multiple aliases for 1-2 versions
   - Consumer code should consistently use `'total_return_percentage'` for new development
