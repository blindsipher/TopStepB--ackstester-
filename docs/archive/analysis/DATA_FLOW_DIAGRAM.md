# DATA FLOW DIAGRAM - COMPLETE SYSTEM TRACE

## OVERVIEW: End-to-End Data Journey

```
FILE SYSTEM                      MEMORY                           OPTIMIZATION                     EXECUTION
    │                               │                                   │                              │
    ▼                               ▼                                   ▼                              │
┌──────────┐                  ┌──────────┐                      ┌──────────────┐                     │
│ CSV/     │                  │ Raw      │                      │ Optuna Trial │                     │
│ Parquet  │──Load───────────▶│ OHLCV    │──Split──────────────▶│ Suggestions  │                     │
│ File     │                  │ DataFrame│                      │              │                     │
└──────────┘                  └──────────┘                      └──────────────┘                     │
                                    │                                   │                              │
                                    │                                   ▼                              │
                                    │                           ┌──────────────┐                     │
                                    │                           │ Parameter    │                     │
                                    │                           │ Validation   │                     │
                                    │                           └──────────────┘                     │
                                    │                                   │                              │
                                    ▼                                   ▼                              │
                            ┌─────────────────┐              ┌──────────────────┐                   │
                            │ DataSplitter    │              │ Strategy         │                   │
                            │                 │              │ Execution        │                   │
                            │ chronological_  │              │                  │                   │
                            │ split() OR      │              │ - Calculate      │                   │
                            │ walk_forward_   │              │   Indicators     │                   │
                            │ splitter()      │              │ - Generate       │                   │
                            └─────────────────┘              │   Signals        │                   │
                                    │                         │ - Position Mgmt  │                   │
                                    │                         └──────────────────┘                   │
                                    ▼                                   │                              │
                            ┌─────────────────┐                        │                              │
                            │ DataSplit       │                        ▼                              │
                            │ (Immutable)     │              ┌──────────────────┐                   │
                            │                 │              │ Performance      │                   │
                            │ ├─train         │              │ Metrics          │                   │
                            │ ├─validation    │              │                  │                   │
                            │ └─test          │              │ - PnL            │                   │
                            │                 │              │ - Sharpe         │                   │
                            │ Metadata:       │              │ - Sortino        │                   │
                            │ ├─temporal order│              │ - Profit Factor  │                   │
                            │ └─gap_days      │              │ - Win Rate       │                   │
                            └─────────────────┘              └──────────────────┘                   │
                                    │                                   │                              │
                                    │                                   ▼                              │
                                    ▼                           ┌──────────────┐                     │
                          ┌───────────────────┐                │ Composite    │                     │
                          │ PipelineOrchestrator│               │ Score        │                     │
                          │                   │                └──────────────┘                     │
                          │ load_data_splits()│                        │                              │
                          └───────────────────┘                        │                              │
                                    │                                   ▼                              │
                                    │                           ┌──────────────┐                     │
                                    ▼                           │ Best Params  │                     │
                          ┌───────────────────┐                │ Selection    │                     │
                          │ Authorization     │                └──────────────┘                     │
                          │ Layer             │                        │                              │
                          │                   │                        │                              │
                          │ get_authorized_   │                        ▼                              │
                          │ data(module,phase)│                ┌──────────────┐                     │
                          └───────────────────┘                │ Deployment   │                     │
                                    │                           │ Engine       │                     │
                                    │                           │              │                     │
                                    ▼                           │ - Template   │                     │
                    ┌─────────────────────────┐                │   Validation │                     │
                    │ PHASE: OPTIMIZATION     │                │ - Parameter  │                     │
                    │                         │                │   Injection  │                     │
                    │ Authorized:             │                └──────────────┘                     │
                    │ ✓ train.copy()          │                        │                              │
                    │ ✓ validation.copy()     │                        │                              │
                    │ ✗ test (WITHHELD)       │                        ▼                              │
                    └─────────────────────────┘                ┌──────────────┐                     │
                                    │                           │ Deployed     │────────────────────▶│
                                    │                           │ Strategy     │                     │
                                    ▼                           │ .py File     │                     │
                          ┌───────────────────┐                └──────────────┘                     │
                          │ ObjectiveFactory  │                                                      │
                          │                   │                                                      │
                          │ create_objective()│                                                      │
                          └───────────────────┘                                                      │
                                    │                                                                 │
                                    ▼                                                                 │
                          ┌───────────────────┐                                                      │
                          │ StatefulObjective │                                                      │
                          │                   │                                                      │
                          │ Per Trial:        │                                                      │
                          │ 1. Fresh strategy │                                                      │
                          │    instance       │                                                      │
                          │ 2. Suggest params │                                                      │
                          │ 3. Validate params│                                                      │
                          │ 4. Run backtest   │                                                      │
                          │ 5. Return score   │                                                      │
                          └───────────────────┘                                                      │
                                    │                                                                 │
                                    ▼                                                                 │
                    ┌─────────────────────────┐                                                      │
                    │ PHASE: VALIDATION       │                                                      │
                    │                         │                                                      │
                    │ Authorized:             │                                                      │
                    │ ✗ train (NOT NEEDED)    │                                                      │
                    │ ✗ validation (NOT NEEDED│                                                      │
                    │ ✓ test.copy()           │                                                      │
                    └─────────────────────────┘                                                      │
                                    │                                                                 │
                                    ▼                                                                 │
                          ┌───────────────────┐                                                      │
                          │ Final Validation  │                                                      │
                          │ on Test Data      │                                                      │
                          └───────────────────┘                                                      │
                                                                                                      │
                                                                                                      ▼
                                                                                              ┌──────────────┐
                                                                                              │ LIVE TRADING │
                                                                                              │ (Deployment) │
                                                                                              └──────────────┘
```

---

## CRITICAL DATA ACCESS TIMELINE

```
TIME AXIS →
────────────────────────────────────────────────────────────────────────────────────────────────

HISTORICAL DATA (2020-01-01 to 2024-12-31)
├──────────────────────────┬──────────────────────┬──────────────────────┤
│      TRAIN DATA          │   VALIDATION DATA    │     TEST DATA        │
│   (60% of data)          │    (20% of data)     │    (20% of data)     │
│                          │                      │                      │
│  Used for:               │  Used for:           │  Used for:           │
│  - Parameter validation  │  - Out-of-sample     │  - Final validation  │
│    (quick check)         │    evaluation        │    ONLY (withheld    │
│                          │  - Performance       │    during opt)       │
│                          │    metrics           │                      │
└──────────────────────────┴──────────────────────┴──────────────────────┘
       ▲                           ▲                        ▲
       │                           │                        │
       │                           │                        │
  GAP DAYS                    GAP DAYS                      │
  (1 day default)             (1 day default)              │
                                                            │
                                                            │
OPTIMIZATION PHASE ───────────────────────────────┐        │
  Access: train + validation                      │        │
  Forbidden: test                                 │        │
                                                  │        │
                                                  │        │
VALIDATION PHASE ─────────────────────────────────┴────────┘
  Access: test only
  Note: train + validation no longer needed


SIGNAL TIMING WITHIN A SINGLE BAR:
──────────────────────────────────────────────────────────────

BAR i-1         BAR i                BAR i+1
│               │                    │
│  Close        │  Open   ...  Close │  Open
│   ↓           │   ↓          ↓     │   ↓
│   │           │   │          │     │   │
│   ├───────────┼───┼──────────┤     │   │
│   │ Indicator │   │ Position │     │   │
│   │ Calc      │   │ Entry    │     │   │
│   │ Signal    │   │ Price    │     │   │
│   │ Generation│   │          │     │   │
│   └───────────┼───┴──────────┤     │   │
│               │              │     │   │
│               │              │     │   │
│ [Bar i-1      │ [Execution   │     │ [Next
│  closes,      │  at Bar i    │     │  trade
│  all data     │  open based  │     │  cycle]
│  known]       │  on i-1      │     │
│               │  signal]     │     │
└───────────────┴──────────────┴─────┴────
    PAST            PRESENT       FUTURE

Key Insight:
- At bar i-1 close: All OHLCV data for bar i-1 is known
- Signal generated using bar i-1 data
- Execution at bar i open (realistic slippage/fill)
- This is the STANDARD backtesting execution model
```

---

## DATA COPY vs REFERENCE MAP

```
ORIGINAL DATA (loaded from file)
    │
    ├─── .copy() ────▶ DataSplit.train
    │                  (independent copy)
    │
    ├─── .copy() ────▶ DataSplit.validation
    │                  (independent copy)
    │
    └─── .copy() ────▶ DataSplit.test
                       (independent copy)


DataSplit (frozen dataclass) - IMMUTABLE
    │
    ├─── .copy() ────▶ Orchestrator internal storage
    │                  (independent copy)
    │
    └─── get_authorized_data()
             │
             ├─── .copy() ────▶ AuthorizedDataAccess.train_data
             │                  (independent copy)
             │
             ├─── .copy() ────▶ AuthorizedDataAccess.validation_data
             │                  (independent copy)
             │
             └─── .copy() ────▶ AuthorizedDataAccess.test_data
                                (independent copy, only in validation phase)


AuthorizedDataAccess
    │
    └─── StatefulObjective.__init__
             │
             └─── Per Trial:
                      │
                      ├─── Fresh strategy instance (no shared state)
                      │
                      └─── execute_strategy(data=authorized_access.validation_data)
                               │
                               └─── DataFrame operations (pandas creates views/copies as needed)


RESULT: Zero shared references between:
- Different splits (train/validation/test)
- Different trials (parallel execution)
- Different phases (optimization/validation)
```

---

## AUTHORIZATION MATRIX

```
┌────────────────────┬──────────┬────────────┬──────────┬──────────┐
│ Module             │ Phase    │ train_data │ val_data │test_data │
├────────────────────┼──────────┼────────────┼──────────┼──────────┤
│ optimization       │ optimize │     ✓      │    ✓     │    ✗     │
│ objective          │ optimize │     ✓      │    ✓     │    ✗     │
│ engine             │ optimize │     ✓      │    ✓     │    ✗     │
├────────────────────┼──────────┼────────────┼──────────┼──────────┤
│ validation         │ validate │     ✗      │    ✗     │    ✓     │
│ testing            │ validate │     ✗      │    ✗     │    ✓     │
├────────────────────┼──────────┼────────────┼──────────┼──────────┤
│ analytics          │ analytics│     ✓      │    ✓     │    ✓     │
│ reporting          │ analytics│     ✓      │    ✓     │    ✓     │
│ deployment         │ analytics│     ✓      │    ✓     │    ✓     │
└────────────────────┴──────────┴────────────┴──────────┴──────────┘

Legend:
✓ = Access GRANTED (data provided via .copy())
✗ = Access DENIED (data is None, withheld)

Security Enforcement:
1. PipelineOrchestrator.get_authorized_data() enforces whitelist
2. Multiple validation checks for test_data presence
3. Audit logging for all access requests
4. Security violation warnings if unauthorized access attempted
```

---

## INDICATOR CALCULATION CAUSALITY

```
INDICATOR: Bollinger Bands Middle (EMA)
───────────────────────────────────────

data.ewm(span=period, adjust=False).mean()

Bar Index:    0    1    2    3    4    5
Close:       100  101  99  102  103  101
EMA:         100 100.5 99.9 100.8 101.7 101.5

Causality Check:
- EMA at bar i uses: bars 0 through i (including current)
- Does NOT use: bars i+1, i+2, ... (future)
✓ CAUSAL - No lookahead bias


INDICATOR: Rolling Standard Deviation
──────────────────────────────────────

data.rolling(window=period).std()

Bar Index:    0    1    2    3    4    5
Close:       100  101  99  102  103  101
Std(3):      NaN  NaN  1.0  1.5  2.0  1.0

Causality Check:
- Std at bar i uses: bars (i-period+1) through i
- Window includes current bar (correct for indicators)
- Does NOT use: bars i+1, i+2, ... (future)
✓ CAUSAL - No lookahead bias


INDICATOR: ATR (Average True Range)
───────────────────────────────────

high_close = (df['high'] - df['close'].shift(1)).abs()

Bar Index:    0    1    2    3    4    5
High:        101  103  100  105  106  103
Close:       100  101   99  102  103  101
PrevClose:   NaN  100  101   99  102  103
high_close:  NaN    3    1    6    4    2

Causality Check:
- Uses .shift(1) to access PREVIOUS close
- True range = max(H-L, H-Cp, L-Cp) where Cp = previous close
- This is the CORRECT ATR formula
✓ CAUSAL - No lookahead bias


SIGNAL: Breakout Detection
──────────────────────────

long_breakout = close > breakout_upper.shift(1)

Bar Index:         0    1    2    3    4    5
Close:            100  101  99  102  103  101
Breakout_Upper:   102  103  101  104  105  103
Upper.shift(1):   NaN  102  103  101  104  105
long_breakout:    NaN    F    F    T    F    F

Timing:
- At bar 3 close: close=102, previous upper=101
- Signal generated: long_breakout = True
- Execution: Entry at bar 4 open

Causality Check:
- Compares current close to PREVIOUS bar's upper band
- Signal known at bar close
- Execution at next bar open
✓ CAUSAL AND CORRECT EXECUTION TIMING
```

---

## PARALLEL TRIAL ISOLATION

```
OPTUNA STUDY (PostgreSQL backed)
    │
    ├─── Worker 1 ───▶ Trial #1
    │                      │
    │                      ├─── Fresh strategy instance (isolated)
    │                      ├─── Copied data (no shared refs)
    │                      └─── Independent evaluation
    │
    ├─── Worker 2 ───▶ Trial #2
    │                      │
    │                      ├─── Fresh strategy instance (isolated)
    │                      ├─── Copied data (no shared refs)
    │                      └─── Independent evaluation
    │
    ├─── Worker 3 ───▶ Trial #3
    │                      │
    │                      ├─── Fresh strategy instance (isolated)
    │                      ├─── Copied data (no shared refs)
    │                      └─── Independent evaluation
    │
    └─── Worker N ───▶ Trial #N
                           │
                           ├─── Fresh strategy instance (isolated)
                           ├─── Copied data (no shared refs)
                           └─── Independent evaluation

State Isolation Mechanisms:
1. StatefulObjective.__call__() creates fresh strategy instance per trial
2. Each trial receives .copy() of authorized data
3. No global state shared between workers
4. PostgreSQL handles trial coordination (lock-free)
5. Each worker process has independent memory space

Result: ZERO cross-contamination between parallel trials
```

---

## MEMORY CORRUPTION PREVENTION

```
DEFENSIVE COPYING CHAIN
═══════════════════════

File Load
    │
    └─▶ DataFrame (raw_data)
            │
            └─▶ data_splitter.py line 76: .sort_values() [creates sorted copy]
                    │
                    ├─▶ line 91: optimize_data = data.iloc[:end].copy()
                    ├─▶ line 92: validate_data = data.iloc[start:end].copy()
                    └─▶ line 93: test_data = data.iloc[start:].copy()
                            │
                            └─▶ DataSplit(train=optimize_data, validation=validate_data, test=test_data)
                                    │
                                    └─▶ PipelineOrchestrator.load_data_splits()
                                            │
                                            └─▶ get_authorized_data()
                                                    │
                                                    ├─▶ line 144: train.copy()
                                                    ├─▶ line 145: validation.copy()
                                                    └─▶ line 158: test.copy()
                                                            │
                                                            └─▶ StatefulObjective receives copied data
                                                                    │
                                                                    └─▶ execute_strategy(data=copied_validation)

TOTAL COPY LAYERS: 3-4 defensive copies
- Layer 1: Data splitting creates independent splits
- Layer 2: DataSplit freezes structure (immutable)
- Layer 3: Orchestrator copies before authorization
- Layer 4: Strategy execution may create internal copies

SHARED REFERENCES: ZERO
CORRUPTION RISK: MINIMAL
```

---

## WALK-FORWARD ANALYSIS FLOW

```
FULL DATASET (10,000 bars)
├─────────────────────────────────────────────────────────────────┤

Split 1:
├──────────────┬──────┬──────┬──────┤
│ Optimize     │ Gap  │ Val  │ Test │
│ 6000 bars    │ 1day │ 2K   │ 2K   │
└──────────────┴──────┴──────┴──────┘
       │                │      │
       └─ Train params  │      └─ Withheld during optimization
                        └─ Evaluate performance

Step forward by 1000 bars →

Split 2:
    ├──────────────┬──────┬──────┬──────┤
    │ Optimize     │ Gap  │ Val  │ Test │
    │ 6000 bars    │ 1day │ 2K   │ 2K   │
    └──────────────┴──────┴──────┴──────┘

Step forward by 1000 bars →

Split 3:
        ├──────────────┬──────┬──────┬──────┤
        │ Optimize     │ Gap  │ Val  │ Test │
        │ 6000 bars    │ 1day │ 2K   │ 2K   │
        └──────────────┴──────┴──────┴──────┘


SECURITY VERIFICATION:
- Each split has independent DataSplit object
- Temporal ordering validated per split
- Test data never provided to optimization
- Gaps prevent data overlap
- Iterator pattern prevents memory accumulation
```

---

**DIAGRAM CREATED:** 2025-10-12
**PURPOSE:** Visual reference for data flow analysis and leakage verification
