# TopStepB Streamlit UI - User Guide

## Overview

The TopStepB Streamlit UI provides a comprehensive graphical interface for the hyperparameter optimization backtesting system. This guide covers all features and usage instructions.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Configuration Page](#configuration-page)
3. [Data Loading](#data-loading)
4. [Optimization Monitoring](#optimization-monitoring)
5. [Results Dashboard](#results-dashboard)
6. [Study History](#study-history)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- Python 3.8 or higher
- PostgreSQL 13+ (for distributed optimization)
- 4GB RAM minimum (8GB recommended)
- Internet connection (for synthetic data generation)

### Installation

All dependencies are included in requirements.txt:

```bash
pip install -r requirements.txt
```

Key UI dependencies:
- streamlit>=1.28.0
- plotly>=5.17.0
- streamlit-aggrid>=0.3.4
- streamlit-option-menu>=0.3.6
- pyyaml>=6.0

### Launching the UI

**Windows:**
```cmd
cd C:\Users\salte\ClaudeProjects\TopStepB--ackstester-
scripts\run_ui.bat
```

**Manual Launch:**
```cmd
python -m streamlit run src/ui/app.py
```

**Access:**
Open your browser to: http://localhost:8501

The UI will automatically open in your default browser when launched.

---

## Configuration Page

The Configuration page is your starting point for setting up optimization runs.

### Navigation

Located in the sidebar, the Configuration page includes five main sections:
1. Strategy & Market Settings
2. Execution Parameters
3. Optimization Settings
4. Validation Tests
5. Configuration Templates

### Strategy & Market Settings

**Strategy Selection**
- Currently supports: Bollinger Squeeze
- Dropdown menu with all available strategies
- Future strategies will appear automatically when added

**Symbol**
- Enter the futures symbol (e.g., ES, NQ, YM, CL)
- Case-insensitive input
- Validated against common futures contracts

**Timeframe**
- Format: number + unit (e.g., "5m", "1h", "1d")
- Supported units: m (minutes), h (hours), d (days)
- Examples: 5m, 15m, 1h, 4h, 1d

**Account Type**
- Select between:
  - COMBINE_50K: $50,000 account size
  - COMBINE_100K: $100,000 account size
  - COMBINE_150K: $150,000 account size
  - EXPRESS_50K: Express $50,000 account
- Affects position sizing and risk management

### Execution Parameters

**Slippage (ticks)**
- Default: 2 ticks
- Range: 0-10 ticks
- Simulates realistic execution delays
- Higher values = more conservative

**Commission (per contract)**
- Default: $2.50
- Range: $0.00-$10.00
- Per-contract round-trip cost
- Includes exchange and broker fees

**Number of Contracts**
- Default: 1
- Range: 1-10 contracts
- Fixed position size for all trades
- Affects profit/loss scaling

### Optimization Settings

**Maximum Trials**
- Default: 100
- Range: 10-10,000 trials
- Total parameter combinations to test
- More trials = better optimization (but longer runtime)

**Maximum Workers**
- Default: 4
- Range: 1-32 workers
- Parallel optimization processes
- Set based on CPU cores available
- More workers = faster optimization

**Memory Per Worker (MB)**
- Default: 2048 MB (2GB)
- Range: 1024-8192 MB
- RAM allocated to each worker process
- Increase if workers crash due to memory

**Optimization Timeout (seconds)**
- Default: 3600 (1 hour)
- Range: 300-86,400 seconds
- Maximum time for entire optimization run
- Set to 0 for unlimited time

### Validation Tests

Enable/disable specific validation tests:

- **In-Sample Validation**: Test on training data
- **Out-of-Sample Validation**: Test on holdout data
- **Permutation Test**: Shuffle data to test for overfitting
- **Monte Carlo Test**: Random simulation testing
- **Noise Injection Test**: Test robustness to noise
- **Regime Test**: Test across market regimes

Toggle switches allow selective enabling of tests. More tests provide better validation but increase runtime.

### Configuration Templates

**Save Configuration**
- Enter a template name
- Click "Save Configuration"
- Stores all current settings to YAML file
- Location: `config/ui_templates/{name}.yaml`
- Useful for reusing common configurations

**Load Configuration**
- Select from saved templates dropdown
- Click "Load Configuration"
- Automatically populates all settings
- Overwrites current configuration

**Export Current Config**
- Click "Export Configuration"
- Downloads current settings as YAML file
- Useful for sharing configurations
- Can be imported on other systems

---

## Data Loading

The Data Loading page handles input data for optimization.

### Two Data Input Methods

#### Method 1: File Upload

**Supported Formats:**
- CSV files (.csv)
- Parquet files (.parquet)

**Required Columns:**
- `timestamp`: DateTime or parseable date string
- `open`: Opening price
- `high`: High price
- `low`: Low price
- `close`: Closing price
- `volume`: Trading volume

**Upload Process:**
1. Click "Browse Files" or drag-and-drop
2. Wait for file processing
3. Review data preview table
4. Check data validation results
5. Proceed to optimization if valid

**Data Validation Checks:**
- Column presence (all required columns exist)
- Data types (numeric prices, datetime timestamps)
- Missing values (NaN detection)
- Price logic (high >= low, etc.)
- Timestamp ordering (chronological)
- Volume validity (non-negative)

#### Method 2: Synthetic Data Generation

**Purpose:**
- Testing without historical data
- Quick optimization experiments
- Development and debugging

**Parameters:**

**Number of Bars**
- Default: 10,000
- Range: 1,000-100,000
- More bars = longer history

**Initial Price**
- Default: $5,000
- Starting price level
- Should match typical instrument price

**Volatility**
- Default: 0.02 (2%)
- Range: 0.001-0.10
- Higher = more price movement

**Trend**
- Default: 0.0001
- Range: -0.001 to 0.001
- Positive = uptrend
- Negative = downtrend

**Generation Process:**
1. Set parameters using sliders
2. Click "Generate Synthetic Data"
3. Wait for generation (instant)
4. Review generated data preview
5. Check data statistics
6. Proceed to optimization

**Synthetic Data Preview:**
- First/last 5 rows display
- Basic statistics (mean, std, min, max)
- Price range visualization
- Volume distribution

### Data Preview

After loading or generating data:
- Table shows first and last 5 rows
- Columns: timestamp, open, high, low, close, volume
- Summary statistics displayed
- Validation status indicators

### Data Requirements

**Minimum Requirements:**
- At least 100 bars (preferably 1,000+)
- Valid OHLCV data structure
- Chronologically ordered timestamps
- No duplicate timestamps
- Reasonable price ranges

**Best Practices:**
- Use clean, validated historical data
- Include sufficient history (multiple market cycles)
- Match timeframe to strategy characteristics
- Verify data quality before optimization

---

## Optimization Monitoring

The Optimization Monitoring page provides real-time tracking of running optimization jobs.

### Real-Time Status

**Study Information:**
- Study name
- Strategy being optimized
- Start time and elapsed duration
- Current status (RUNNING, COMPLETE, FAILED)

**Trial Progress:**
- Total trials completed
- Trials remaining
- Progress bar visualization
- Success/failure/pruned counts

**Best Result Tracking:**
- Current best trial number
- Best composite score achieved
- Best parameters found
- Metric breakdown (Sharpe, Sortino, Calmar, Return, etc.)

### Trial Statistics

**Recent Trials Table:**
- Trial number
- Status (COMPLETE, PRUNED, FAIL)
- Composite score
- Key parameters
- Duration
- Timestamp

Displays last 20 trials by default, auto-refreshes.

### Performance Metrics

**Real-time Metrics Display:**
- Sharpe Ratio: Risk-adjusted return
- Sortino Ratio: Downside risk-adjusted return
- Calmar Ratio: Return vs. max drawdown
- Max Drawdown: Largest peak-to-trough decline
- Total Return: Cumulative profit/loss percentage
- Win Rate: Percentage of profitable trades

### Auto-Refresh Controls

**Refresh Settings:**
- Auto-refresh toggle (ON/OFF)
- Refresh interval (5-60 seconds)
- Manual refresh button

**Usage Tips:**
- Enable auto-refresh for active monitoring
- Disable to reduce database load
- Use manual refresh for occasional checks

### Connection Status

**Database Connection Indicator:**
- Green: Connected to PostgreSQL
- Red: Connection failed, using SQLite fallback
- Yellow: Connecting/reconnecting

**Connection Details:**
- Host and port information
- Database name
- Connection pool status

---

## Results Dashboard

The Results Dashboard provides comprehensive analysis of completed optimization runs.

### Study Selection

**Study Browser:**
- Dropdown list of all completed studies
- Sorted by completion date (newest first)
- Displays study name, strategy, and timestamp
- Select study to load results

**Study Information Card:**
- Study name and ID
- Strategy optimized
- Symbol and timeframe
- Start and end times
- Total trials completed
- Best trial metrics

### Best Trial Analysis

**Parameter Display:**
- All optimized parameters
- Best values found
- Parameter ranges tested
- Parameter importance (if available)

**Performance Metrics:**
- Composite Score (weighted)
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Max Drawdown
- Total Return
- Win Rate
- Profit Factor
- Average Trade
- Total Trades

**Metric Explanations:**
Hover over metric names for detailed explanations of each performance measure.

### Trial History Visualization

**Interactive Plotly Charts:**

1. **Composite Score Timeline**
   - X-axis: Trial number
   - Y-axis: Composite score
   - Best trials highlighted
   - Hover for details

2. **Parameter Evolution**
   - Shows parameter values over trials
   - Multiple parameters overlaid
   - Identifies convergence patterns

3. **Metric Comparison**
   - Compare multiple metrics
   - Correlation visualization
   - Trade-off analysis

**Chart Interactions:**
- Zoom: Click and drag
- Pan: Shift + drag
- Reset: Double-click
- Export: Camera icon (top-right)

### Trial Details Table

**Comprehensive Trial List:**
- All trials with full details
- Sortable by any column
- Filterable by status
- Pagination for large result sets

**Columns:**
- Trial number
- Status
- Composite score
- All parameters
- All performance metrics
- Duration
- Timestamp

**Table Features:**
- Sort ascending/descending
- Filter by value ranges
- Export to CSV
- Copy to clipboard

### Export Functionality

**Export Options:**

1. **Export Best Parameters**
   - YAML format
   - Ready for live deployment
   - Includes metadata
   - Location: `results/best_params_{study_name}.yaml`

2. **Export All Results**
   - CSV format
   - All trials and metrics
   - For external analysis
   - Location: `results/study_{study_name}_results.csv`

3. **Export Charts**
   - PNG/SVG format
   - High-resolution images
   - For reports and presentations
   - Save via chart toolbar

---

## Study History

The Study History page provides access to all historical optimization runs.

### Study Browser

**Study List:**
- All studies (active and completed)
- Sorted by date (newest first)
- Color-coded by status:
  - Green: COMPLETE
  - Blue: RUNNING
  - Red: FAILED
  - Gray: PENDING

**Study Cards:**
Each study displays:
- Study name
- Strategy type
- Symbol and timeframe
- Total trials
- Best score achieved
- Start/end timestamps
- Status indicator

### Study Details

**Click any study to view:**

**Summary Information:**
- Study configuration
- Optimization settings
- Validation tests enabled
- Execution parameters

**Progress Tracking:**
- Trials completed/total
- Success/failure/pruned counts
- Current best trial
- Elapsed time

**Quick Actions:**
- View Results: Navigate to Results Dashboard
- Continue Optimization: Resume if stopped
- Export Data: Download study data
- Delete Study: Remove from database

### Study Management

**Delete Studies:**
1. Select studies using checkboxes
2. Click "Delete Selected Studies"
3. Confirm deletion
4. Studies removed from database

**Warning:** Deletion is permanent and cannot be undone.

**Study Search:**
- Filter by study name
- Filter by strategy
- Filter by symbol
- Filter by date range
- Filter by status

**Study Statistics:**
- Total studies run
- Total trials completed
- Average study duration
- Best overall scores

---

## Advanced Features

### Configuration Best Practices

**Trial Count Selection:**
- Simple strategies: 100-500 trials
- Complex strategies: 1,000-5,000 trials
- Production optimization: 5,000-10,000 trials

**Worker Configuration:**
- Local development: 2-4 workers
- High-end workstation: 8-16 workers
- AWS deployment: 32+ workers

**Memory Allocation:**
- Small datasets (<100K bars): 1024 MB
- Medium datasets (100K-1M bars): 2048 MB
- Large datasets (>1M bars): 4096 MB

### PostgreSQL Configuration

**Connection Settings:**
Edit `TopStepB/optimization/config/optuna_config.py`:

```python
@dataclass
class StorageConfig:
    host: str = "localhost"
    port: int = 5433
    database: str = "topstepb_optimization"
    username: str = "postgres"
    password: str = "AdminAdmin"
```

**Connection String:**
```
postgresql://postgres:AdminAdmin@localhost:5433/topstepb_optimization
```

**Fallback Behavior:**
If PostgreSQL connection fails, the system automatically falls back to SQLite storage in the local results directory.

### Performance Optimization

**Speed Up Optimization:**
1. Increase max workers (more parallel trials)
2. Reduce validation tests (fewer computations)
3. Use smaller datasets for initial runs
4. Enable pruning (stops poor trials early)
5. Use distributed PostgreSQL storage

**Reduce Memory Usage:**
1. Decrease memory per worker
2. Reduce number of bars in dataset
3. Limit concurrent workers
4. Enable garbage collection
5. Use data streaming

### Integration with CLI

The UI is built on top of the existing CLI system. You can:

**Run CLI Directly:**
```bash
python TopStepB/main_runner.py \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 20m \
  --max-trials 100 \
  --max-workers 4
```

**View CLI Results in UI:**
All CLI optimizations appear in the UI if using PostgreSQL storage. Studies created via CLI can be monitored and analyzed in the Results Dashboard.

**Export UI Config to CLI:**
Export configuration from UI and use in CLI scripts for reproducible runs.

---

## Troubleshooting

### Common Issues

#### UI Won't Launch

**Symptom:** Error when running run_ui.bat or streamlit run command

**Solutions:**
1. Verify Python installation: `python --version`
2. Check Streamlit installation: `pip show streamlit`
3. Reinstall dependencies: `pip install -r requirements.txt --upgrade`
4. Check for port conflicts: `netstat -ano | findstr :8501`
5. Try alternate port: `streamlit run src/ui/app.py --server.port 8502`

#### Database Connection Failed

**Symptom:** Red connection status, "Using SQLite fallback" message

**Solutions:**
1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5433`
2. Check credentials in optuna_config.py
3. Verify database exists: `psql -U postgres -l`
4. Check firewall settings (allow port 5433)
5. Review PostgreSQL logs for errors

**Fallback Behavior:**
The system automatically falls back to SQLite storage when PostgreSQL is unavailable. Features remain functional but distributed optimization is disabled.

#### Data Upload Fails

**Symptom:** Error message after uploading CSV/Parquet file

**Solutions:**
1. Verify file format (CSV or Parquet only)
2. Check required columns exist (timestamp, OHLCV)
3. Validate timestamp format (ISO 8601 or common formats)
4. Check for missing values (NaN)
5. Verify file size (< 500MB recommended)
6. Try converting to Parquet for large files

#### Optimization Not Starting

**Symptom:** Click "Start Optimization" but nothing happens

**Solutions:**
1. Check configuration validation (red error messages)
2. Verify data is loaded (preview shows data)
3. Check subprocess logs in logs/ directory
4. Verify main_runner.py exists and is executable
5. Check available system resources (RAM, CPU)

#### Results Not Displaying

**Symptom:** Study appears in list but results page is empty

**Solutions:**
1. Verify study completed successfully
2. Check database connection status
3. Wait for study to finish (check monitoring page)
4. Refresh page manually
5. Check for error messages in study details

### Performance Issues

#### Slow UI Response

**Causes:**
- Large datasets loaded
- Many concurrent users
- Auto-refresh enabled with short interval
- Database query timeout

**Solutions:**
1. Disable auto-refresh when not needed
2. Increase refresh interval to 30-60 seconds
3. Limit data preview rows
4. Close unused browser tabs
5. Restart Streamlit application

#### High Memory Usage

**Causes:**
- Multiple datasets loaded
- Many trials in memory
- Memory leaks in long-running sessions

**Solutions:**
1. Restart Streamlit periodically
2. Clear browser cache
3. Reduce dataset size
4. Limit number of trials displayed
5. Close other applications

### Data Issues

#### Invalid Data Error

**Common Causes:**
- Missing required columns
- Wrong data types (strings instead of numbers)
- Invalid timestamps
- Duplicate timestamps
- Non-chronological data

**Validation Checklist:**
- [ ] All columns present (timestamp, OHLCV)
- [ ] Timestamps parseable as dates
- [ ] Prices are numeric
- [ ] High >= Low for all bars
- [ ] Close between High and Low
- [ ] Volume is non-negative
- [ ] Timestamps in ascending order
- [ ] No duplicate timestamps

#### Data Quality Issues

**Indicators:**
- Unrealistic optimization results
- Overfitting warnings
- Poor out-of-sample performance
- Excessive drawdowns

**Solutions:**
1. Review data source quality
2. Check for data gaps or errors
3. Validate against known market data
4. Test with synthetic data first
5. Apply data cleaning procedures

### Getting Help

**Documentation Resources:**
- This User Guide: `docs/UI_USER_GUIDE.md`
- Architecture Documentation: `docs/STREAMLIT_UI_ARCHITECTURE.md`
- Main README: `README.md`
- PostgreSQL Setup: `README-POSTGRESQL.md`
- Quick Start: `README-QUICKSTART.md`

**Log Files:**
- Streamlit logs: Console output from run_ui.bat
- Optimization logs: `logs/` directory
- Database logs: PostgreSQL log directory
- Error logs: `logs/root_debug.log`

**Contact:**
- GitHub Issues: [Repository URL]
- Author: blindsipher
- Project: TopStepB Hyperparameter Optimization Factory

---

## Appendix

### Keyboard Shortcuts

**Streamlit Shortcuts:**
- `Ctrl+R` / `Cmd+R`: Refresh page
- `Ctrl+Shift+R` / `Cmd+Shift+R`: Hard refresh
- `Ctrl+K` / `Cmd+K`: Focus search
- `Ctrl+Shift+C` / `Cmd+Shift+C`: Copy to clipboard

### File Locations

**Configuration:**
- UI Templates: `config/ui_templates/`
- Optuna Config: `TopStepB/optimization/config/optuna_config.py`
- Main Config: `config/`

**Data:**
- Uploaded files: Stored in memory (not persisted)
- Synthetic data: Generated on-demand
- Results: `results/` directory

**Logs:**
- Application logs: `logs/`
- Streamlit logs: Console output
- Database logs: PostgreSQL data directory

**Scripts:**
- UI Launcher: `scripts/run_ui.bat`
- Main Runner: `TopStepB/main_runner.py`

### API Reference

The UI is built using:
- **Streamlit**: UI framework
- **Plotly**: Interactive charts
- **Pandas**: Data manipulation
- **SQLAlchemy**: Database interface
- **Optuna**: Optimization framework

**Key Modules:**
- `src/ui/app.py`: Main application entry point
- `src/ui/components/`: UI components
- `src/ui/services/`: Backend services
- `src/ui/utils/`: Utility functions

### Version Information

**UI Version:** 1.0.0
**Implementation Date:** October 11, 2025
**Platform:** TopStepB Hyperparameter Optimization Factory
**Author:** blindsipher

**Changelog:**
- v1.0.0 (2025-10-11): Initial Streamlit UI release
  - Configuration page with validation
  - Data loading (file upload & synthetic)
  - Real-time optimization monitoring
  - Results dashboard with Plotly charts
  - Study history browser
  - PostgreSQL integration
  - Export functionality

---

**End of User Guide**

For technical details and architecture information, see `docs/STREAMLIT_UI_ARCHITECTURE.md`.
