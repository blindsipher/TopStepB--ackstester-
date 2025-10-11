# TopStepB Streamlit UI - Architecture Documentation

## Document Information
- **Version**: 1.0.0
- **Date**: October 11, 2025
- **Author**: blindsipher
- **Purpose**: Technical architecture documentation for the Streamlit UI

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Structure](#component-structure)
4. [Service Layer](#service-layer)
5. [Data Flow](#data-flow)
6. [Integration Points](#integration-points)
7. [State Management](#state-management)
8. [Database Schema](#database-schema)
9. [Security Considerations](#security-considerations)
10. [Performance Optimization](#performance-optimization)
11. [Future Enhancements](#future-enhancements)

---

## Overview

### Purpose

The Streamlit UI provides a comprehensive graphical interface for the TopStepB hyperparameter optimization system. It enables users to configure, launch, monitor, and analyze optimization runs without requiring command-line knowledge.

### Design Goals

1. **User-Friendly**: Intuitive interface for all user levels
2. **Real-Time**: Live monitoring of optimization progress
3. **Integrated**: Seamless integration with existing CLI system
4. **Scalable**: Support for distributed optimization
5. **Maintainable**: Clean separation of concerns
6. **Extensible**: Easy to add new features

### Technology Stack

**Frontend**:
- Streamlit 1.28.0+ (UI framework)
- Plotly 5.17.0+ (Interactive charts)
- streamlit-aggrid 0.3.4+ (Advanced data grids)
- streamlit-option-menu 0.3.6+ (Navigation menu)

**Backend**:
- Python 3.8+
- SQLAlchemy (Database ORM)
- PostgreSQL 13+ (Primary storage)
- SQLite (Fallback storage)
- Optuna (Optimization framework)

**Integration**:
- Subprocess (CLI execution)
- YAML (Configuration storage)
- CSV/Parquet (Data import/export)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI Layer                     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │  Config  │   Data   │ Monitor  │ Results  │ History  │  │
│  │   Page   │  Loader  │   Page   │   Page   │   Page   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  ┌─────────────────────────┬──────────────────────────────┐ │
│  │   PipelineService       │    DatabaseService           │ │
│  │  - CLI Integration      │    - PostgreSQL Interface    │ │
│  │  - Subprocess Mgmt      │    - Optuna Queries          │ │
│  └─────────────────────────┴──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Systems                          │
│  ┌─────────────────────────┬──────────────────────────────┐ │
│  │   main_runner.py        │    PostgreSQL Database       │ │
│  │  - Optimization Engine  │    - Optuna Storage          │ │
│  │  - Strategy Execution   │    - Study/Trial Data        │ │
│  └─────────────────────────┴──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/ui/
├── app.py                          # Main Streamlit application
├── __init__.py
├── components/                     # UI pages/components
│   ├── __init__.py
│   ├── configuration.py           # Configuration page
│   ├── data_loader.py             # Data loading page
│   ├── optimization_monitor.py    # Monitoring page
│   ├── results_dashboard.py       # Results page
│   └── study_browser.py           # Study history page
├── services/                       # Backend integration
│   ├── __init__.py
│   ├── pipeline_service.py        # CLI interface service
│   └── database_service.py        # Database interface service
└── utils/                          # Utilities
    ├── __init__.py
    ├── session_state.py           # State management
    ├── validators.py              # Input validation
    └── formatters.py              # Display formatting
```

---

## Component Structure

### Main Application (app.py)

**Responsibility**: Application entry point and navigation

**Key Functions**:
- Initialize Streamlit configuration
- Setup multi-page navigation
- Manage sidebar menu
- Initialize session state
- Route to appropriate page

**Code Structure**:
```python
def main():
    # Configure Streamlit
    st.set_page_config(...)

    # Initialize session state
    initialize_session_state()

    # Render navigation menu
    selected_page = render_menu()

    # Route to page
    if selected_page == "Configuration":
        configuration.render()
    elif selected_page == "Data Loading":
        data_loader.render()
    # ... etc
```

### Configuration Component (configuration.py)

**Responsibility**: Optimization configuration interface

**Features**:
- Strategy selection
- Market parameters (symbol, timeframe, account type)
- Execution parameters (slippage, commission, contracts)
- Optimization settings (trials, workers, memory, timeout)
- Validation test selection
- Configuration templates (save/load/export)

**Key Classes**:
```python
class ConfigurationPage:
    def render(self):
        # Render configuration form

    def validate_config(self):
        # Validate user inputs

    def save_template(self):
        # Save configuration to YAML

    def load_template(self):
        # Load configuration from YAML
```

**Validation Flow**:
```
User Input → ConfigurationValidator → Session State → Display
                     │
                     ▼
              Error Messages
```

### Data Loader Component (data_loader.py)

**Responsibility**: Data input and validation

**Features**:
- File upload (CSV/Parquet)
- Synthetic data generation
- Data validation
- Data preview
- Statistics display

**Upload Flow**:
```
File Upload → Parse Data → Validate → Store in Session → Preview
                                │
                                ▼
                          Validation Errors
```

**Synthetic Data Flow**:
```
User Parameters → Generate Data → Validate → Store → Preview
```

**Key Functions**:
```python
def upload_file(uploaded_file):
    # Parse CSV/Parquet file
    # Validate data structure
    # Return validated dataframe

def generate_synthetic_data(params):
    # Generate OHLCV bars
    # Add realistic patterns
    # Return synthetic dataframe

def validate_data(df):
    # Check columns
    # Validate types
    # Check logic
    # Return validation results
```

### Optimization Monitor Component (optimization_monitor.py)

**Responsibility**: Real-time monitoring of optimization runs

**Features**:
- Study status display
- Trial progress tracking
- Best trial monitoring
- Recent trials table
- Auto-refresh capability

**Monitoring Flow**:
```
Database Query → Parse Results → Format Display → Render UI
      ▲                                              │
      └──────────────── Auto-refresh ────────────────┘
```

**Key Functions**:
```python
def render_monitor():
    # Get active study
    # Query database for status
    # Display progress
    # Show best trial
    # List recent trials

def auto_refresh():
    # Check refresh interval
    # Trigger rerun if needed
```

### Results Dashboard Component (results_dashboard.py)

**Responsibility**: Results visualization and analysis

**Features**:
- Study selection
- Best trial display
- Interactive charts (Plotly)
- Trial comparison
- Export functionality

**Visualization Flow**:
```
Study Selection → Query Trials → Process Data → Generate Charts → Display
                                                       │
                                                       ▼
                                                  Export Options
```

**Chart Types**:
1. **Composite Score Timeline**: Trial performance over time
2. **Parameter Evolution**: How parameters changed
3. **Metric Comparison**: Compare different metrics

**Key Functions**:
```python
def render_results():
    # Select study
    # Load trials
    # Display best trial
    # Render charts
    # Provide export options

def create_timeline_chart(trials):
    # Process trial data
    # Create Plotly figure
    # Return interactive chart

def export_results(study, format):
    # Format data for export
    # Generate file
    # Provide download
```

### Study Browser Component (study_browser.py)

**Responsibility**: Study history and management

**Features**:
- Historical studies list
- Study details view
- Study deletion
- Quick actions
- Study statistics

**Browser Flow**:
```
Load Studies → Display Cards → User Action → Execute → Refresh
                                    │
                                    ▼
                        (View/Export/Delete)
```

**Key Functions**:
```python
def render_browser():
    # Load all studies
    # Display study cards
    # Handle user actions

def delete_study(study_name):
    # Confirm deletion
    # Remove from database
    # Refresh display
```

---

## Service Layer

### PipelineService (pipeline_service.py)

**Responsibility**: Interface between UI and CLI optimization engine

**Key Responsibilities**:
1. Build command-line arguments from UI config
2. Launch optimization subprocess
3. Monitor process status
4. Handle process termination

**Architecture**:
```python
class PipelineService:
    def __init__(self):
        self.processes = {}  # Active subprocess tracking

    def build_command(self, config):
        """Build CLI command from UI config"""
        # Convert UI config to CLI args
        # Return command string

    def launch_optimization(self, config, data):
        """Launch optimization subprocess"""
        # Build command
        # Start subprocess
        # Store process reference
        # Return process ID

    def get_status(self, process_id):
        """Get subprocess status"""
        # Check if running
        # Return status

    def terminate(self, process_id):
        """Terminate subprocess"""
        # Send termination signal
        # Clean up resources
```

**Command Building Example**:
```python
def build_command(self, config):
    cmd = [
        "python",
        "TopStepB/main_runner.py",
        f"--strategy={config['strategy']}",
        f"--symbol={config['symbol']}",
        f"--timeframe={config['timeframe']}",
        f"--max-trials={config['max_trials']}",
        # ... more args
    ]
    return " ".join(cmd)
```

**Integration Flow**:
```
UI Config → build_command() → subprocess.Popen() → main_runner.py
                                        │
                                        ▼
                              PostgreSQL (results)
```

### DatabaseService (database_service.py)

**Responsibility**: PostgreSQL/Optuna database interface

**Key Responsibilities**:
1. Manage database connections
2. Query Optuna studies
3. Retrieve trial data
4. Handle connection pooling

**Architecture**:
```python
class DatabaseService:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string, pool_size=5)
        self.session_factory = sessionmaker(bind=self.engine)

    def get_studies(self):
        """Get all optimization studies"""
        # Query study table
        # Return study list

    def get_study_trials(self, study_name):
        """Get all trials for a study"""
        # Query trial table
        # Return trial data

    def get_best_trial(self, study_name):
        """Get best trial for a study"""
        # Query and sort trials
        # Return best trial

    def delete_study(self, study_name):
        """Delete a study and its trials"""
        # Begin transaction
        # Delete trials
        # Delete study
        # Commit transaction
```

**Connection Management**:
```python
@contextmanager
def get_session(self):
    """Context manager for database sessions"""
    session = self.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Query Example**:
```python
def get_study_trials(self, study_name):
    with self.get_session() as session:
        trials = session.query(Trial)\
            .join(Study)\
            .filter(Study.study_name == study_name)\
            .all()
        return [self._trial_to_dict(t) for t in trials]
```

**Connection Pooling**:
- Pool size: 5 connections
- Max overflow: 10 connections
- Recycle time: 3600 seconds
- Echo SQL: False (production)

---

## Data Flow

### Configuration to Execution Flow

```
User Input (UI)
    │
    ▼
ConfigurationValidator
    │
    ▼
Session State (st.session_state)
    │
    ▼
PipelineService.build_command()
    │
    ▼
subprocess.Popen(command)
    │
    ▼
main_runner.py (CLI)
    │
    ▼
Optimization Engine
    │
    ▼
PostgreSQL (Optuna)
```

### Monitoring Flow

```
PostgreSQL Database
    │
    ▼
DatabaseService.get_study_trials()
    │
    ▼
Data Processing (format, aggregate)
    │
    ▼
UI Display (tables, charts)
    │
    ▼
Auto-refresh (if enabled)
    │
    └─→ Loop back to query
```

### Results Visualization Flow

```
Study Selection (UI)
    │
    ▼
DatabaseService.get_study_trials()
    │
    ▼
Data Processing
    ├─→ Best Trial Calculation
    ├─→ Trial History Processing
    └─→ Chart Data Preparation
        │
        ▼
    Plotly Chart Generation
        │
        ▼
    Interactive Display
```

### Data Upload Flow

```
File Upload (UI)
    │
    ▼
File Parser (CSV/Parquet)
    │
    ▼
DataValidator
    ├─→ Column Check
    ├─→ Type Validation
    ├─→ Logic Validation
    └─→ Completeness Check
        │
        ▼
    Validation Results
        │
        ├─→ Success: Store in Session
        └─→ Failure: Display Errors
```

---

## Integration Points

### CLI Integration

**Integration Method**: Subprocess execution with argument passing

**Communication**:
- UI → CLI: Command-line arguments
- CLI → UI: PostgreSQL database (results)
- CLI → UI: File system (logs)

**CLI Command Format**:
```bash
python "TopStepB/main_runner.py" \
  --strategy bollinger_squeeze \
  --symbol ES \
  --timeframe 20m \
  --account-type COMBINE_50K \
  --slippage 2 \
  --commission 2.5 \
  --contracts 1 \
  --max-trials 100 \
  --max-workers 4 \
  --memory-limit 2048 \
  --timeout 3600 \
  --data-file /path/to/data.csv \
  --validation-tests in_sample,out_sample
```

**Argument Mapping**:
| UI Config | CLI Argument | Type | Example |
|-----------|--------------|------|---------|
| strategy | --strategy | string | bollinger_squeeze |
| symbol | --symbol | string | ES |
| timeframe | --timeframe | string | 20m |
| account_type | --account-type | string | COMBINE_50K |
| slippage | --slippage | int | 2 |
| commission | --commission | float | 2.5 |
| contracts | --contracts | int | 1 |
| max_trials | --max-trials | int | 100 |
| max_workers | --max-workers | int | 4 |
| memory_limit | --memory-limit | int | 2048 |
| timeout | --timeout | int | 3600 |

### Database Integration

**Database Type**: PostgreSQL 13+
**ORM**: SQLAlchemy
**Schema**: Optuna standard schema

**Connection Configuration**:
```python
# In optuna_config.py
@dataclass
class StorageConfig:
    host: str = "localhost"
    port: int = 5433
    database: str = "topstepb_optimization"
    username: str = "postgres"
    password: str = "AdminAdmin"

    @property
    def connection_string(self):
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
```

**Tables Used**:
1. **studies**: Optuna study metadata
2. **trials**: Trial data and results
3. **trial_params**: Parameter values for each trial
4. **trial_values**: Objective values for each trial
5. **trial_user_attributes**: Custom trial metadata

**Query Patterns**:
```sql
-- Get all studies
SELECT * FROM studies ORDER BY datetime_start DESC;

-- Get study trials
SELECT t.* FROM trials t
JOIN studies s ON t.study_id = s.study_id
WHERE s.study_name = 'bollinger_squeeze_ES_20m_20251011';

-- Get best trial
SELECT t.* FROM trials t
JOIN studies s ON t.study_id = s.study_id
WHERE s.study_name = 'study_name'
ORDER BY t.value DESC LIMIT 1;
```

**Connection Pooling**:
```python
engine = create_engine(
    connection_string,
    pool_size=5,           # 5 persistent connections
    max_overflow=10,       # 10 additional on demand
    pool_recycle=3600,     # Recycle after 1 hour
    pool_pre_ping=True     # Verify connection before use
)
```

### File System Integration

**Configuration Storage**:
- Location: `config/ui_templates/`
- Format: YAML
- Structure:
```yaml
strategy: bollinger_squeeze
symbol: ES
timeframe: 20m
account_type: COMBINE_50K
# ... more config
```

**Data Storage**:
- Uploaded files: In-memory (not persisted)
- Exported results: `results/` directory
- Logs: `logs/` directory

**Export Formats**:
1. **Best Parameters**: YAML format
   ```yaml
   study_name: bollinger_squeeze_ES_20m_20251011
   best_trial: 42
   parameters:
     bb_period: 20
     bb_std: 2.0
     # ...
   metrics:
     composite_score: 0.85
     sharpe_ratio: 1.5
     # ...
   ```

2. **Full Results**: CSV format
   ```csv
   trial_number,status,composite_score,sharpe_ratio,sortino_ratio,...
   1,COMPLETE,0.45,1.2,1.5,...
   2,PRUNED,0.20,0.5,0.8,...
   # ...
   ```

---

## State Management

### Streamlit Session State

**Purpose**: Maintain state across page navigation and reruns

**Key State Variables**:
```python
st.session_state = {
    # Configuration
    'config': {
        'strategy': 'bollinger_squeeze',
        'symbol': 'ES',
        # ... more config
    },

    # Data
    'data': pd.DataFrame(),  # Loaded/generated data
    'data_source': 'file',   # 'file' or 'synthetic'

    # Validation
    'validation_errors': [],
    'config_valid': False,
    'data_valid': False,

    # Monitoring
    'current_study': 'study_name',
    'auto_refresh': True,
    'refresh_interval': 10,

    # Results
    'selected_study': 'study_name',
    'chart_data': {},

    # Templates
    'saved_templates': [],
    'current_template': None
}
```

**Initialization**:
```python
def initialize_session_state():
    """Initialize session state with defaults"""
    if 'config' not in st.session_state:
        st.session_state.config = get_default_config()
    if 'data' not in st.session_state:
        st.session_state.data = None
    # ... initialize other state
```

**State Persistence**:
- Session state persists across page navigation
- State resets on browser refresh
- Configuration templates persist to disk (YAML)

**State Update Pattern**:
```python
# Read from state
config = st.session_state.config

# Modify
config['max_trials'] = 100

# Write back to state
st.session_state.config = config
```

### Configuration Templates

**Purpose**: Save and load common configurations

**Template Structure**:
```python
{
    'name': 'my_template',
    'timestamp': '2025-10-11 21:00:00',
    'config': {
        # Full configuration
    }
}
```

**Save Flow**:
```
User Input → Validate → Format → Write YAML → Update Template List
```

**Load Flow**:
```
Select Template → Read YAML → Validate → Update Session State → Render
```

---

## Database Schema

### Optuna Tables (Standard Schema)

**studies**:
```sql
CREATE TABLE studies (
    study_id INTEGER PRIMARY KEY,
    study_name VARCHAR UNIQUE,
    direction VARCHAR,  -- 'maximize' or 'minimize'
    user_attrs JSON,
    system_attrs JSON,
    datetime_start TIMESTAMP
);
```

**trials**:
```sql
CREATE TABLE trials (
    trial_id INTEGER PRIMARY KEY,
    study_id INTEGER REFERENCES studies(study_id),
    number INTEGER,
    state VARCHAR,  -- 'COMPLETE', 'PRUNED', 'FAIL'
    value FLOAT,    -- Objective value
    datetime_start TIMESTAMP,
    datetime_complete TIMESTAMP,
    UNIQUE(study_id, number)
);
```

**trial_params**:
```sql
CREATE TABLE trial_params (
    param_id INTEGER PRIMARY KEY,
    trial_id INTEGER REFERENCES trials(trial_id),
    param_name VARCHAR,
    param_value VARCHAR,
    distribution JSON
);
```

**trial_values**:
```sql
CREATE TABLE trial_values (
    trial_value_id INTEGER PRIMARY KEY,
    trial_id INTEGER REFERENCES trials(trial_id),
    objective INTEGER,  -- 0 for single objective
    value FLOAT
);
```

**trial_user_attributes**:
```sql
CREATE TABLE trial_user_attributes (
    trial_user_attribute_id INTEGER PRIMARY KEY,
    trial_id INTEGER REFERENCES trials(trial_id),
    key VARCHAR,
    value VARCHAR
);
```

### Custom Attributes

The UI stores additional metadata in trial user attributes:

```python
trial.set_user_attr('sharpe_ratio', 1.5)
trial.set_user_attr('sortino_ratio', 1.8)
trial.set_user_attr('max_drawdown', -0.15)
trial.set_user_attr('total_return', 0.45)
trial.set_user_attr('win_rate', 0.60)
# ... more metrics
```

### Indexing Strategy

**Performance Indexes**:
```sql
CREATE INDEX idx_study_name ON studies(study_name);
CREATE INDEX idx_trial_study ON trials(study_id);
CREATE INDEX idx_trial_number ON trials(study_id, number);
CREATE INDEX idx_trial_state ON trials(state);
CREATE INDEX idx_trial_value ON trials(value);
```

---

## Security Considerations

### Input Validation

**All user inputs are validated**:
1. Type checking
2. Range validation
3. Format validation
4. SQL injection prevention (parameterized queries)
5. Path traversal prevention

**Example Validation**:
```python
class ConfigurationValidator:
    @staticmethod
    def validate_symbol(symbol: str) -> Tuple[bool, str]:
        if not symbol:
            return False, "Symbol is required"
        if not symbol.isalnum():
            return False, "Symbol must be alphanumeric"
        if len(symbol) > 10:
            return False, "Symbol too long"
        return True, ""
```

### Database Security

**Connection Security**:
- Password stored in config (not hardcoded)
- Connection pooling with timeout
- Parameterized queries (SQL injection prevention)
- Transaction rollback on errors

**Example Safe Query**:
```python
# Safe - parameterized
study = session.query(Study).filter(
    Study.study_name == study_name
).first()

# Unsafe - string concatenation (NEVER DO THIS)
# query = f"SELECT * FROM studies WHERE study_name = '{study_name}'"
```

### File Upload Security

**Validation**:
- File type checking (CSV/Parquet only)
- File size limits
- Content validation
- No file execution

**Example**:
```python
def validate_upload(file):
    # Check extension
    if not file.name.endswith(('.csv', '.parquet')):
        return False, "Invalid file type"

    # Check size (500 MB max)
    if file.size > 500 * 1024 * 1024:
        return False, "File too large"

    return True, ""
```

### Subprocess Security

**Sandboxing**:
- No shell=True (prevents command injection)
- Limited execution environment
- Process timeout
- Resource limits

**Example**:
```python
# Safe
subprocess.Popen(
    command,
    shell=False,  # Prevent shell injection
    timeout=3600  # Limit execution time
)

# Unsafe (NEVER DO THIS)
# subprocess.Popen(command, shell=True)
```

---

## Performance Optimization

### Database Query Optimization

**Strategies**:
1. **Connection Pooling**: Reuse database connections
2. **Indexed Queries**: Use indexed columns in WHERE clauses
3. **Limit Results**: Pagination for large result sets
4. **Lazy Loading**: Load data only when needed
5. **Caching**: Cache frequently accessed data

**Example Optimization**:
```python
# Optimized - with limit and index
def get_recent_trials(study_name, limit=20):
    return session.query(Trial)\
        .filter(Trial.study_name == study_name)\
        .order_by(Trial.number.desc())\
        .limit(limit)\
        .all()

# Unoptimized - no limit
# trials = session.query(Trial).all()  # Could be thousands
```

### UI Rendering Optimization

**Strategies**:
1. **Lazy Loading**: Render components only when visible
2. **Pagination**: Display large datasets in chunks
3. **Debouncing**: Delay actions until user stops typing
4. **Caching**: Cache computed values with @st.cache_data
5. **Virtual Scrolling**: Render only visible rows

**Example Caching**:
```python
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_study_data(study_name):
    """Load study data with caching"""
    # Expensive database query
    return db_service.get_study_trials(study_name)
```

### Auto-Refresh Optimization

**Smart Refresh**:
```python
def auto_refresh():
    if st.session_state.auto_refresh:
        interval = st.session_state.refresh_interval

        # Only refresh if study is active
        study_status = get_study_status()
        if study_status == 'RUNNING':
            time.sleep(interval)
            st.rerun()
        else:
            # Don't refresh completed studies
            st.session_state.auto_refresh = False
```

### Chart Rendering Optimization

**Plotly Optimization**:
```python
def create_chart(trials):
    # Limit data points for performance
    if len(trials) > 1000:
        trials = trials[::10]  # Every 10th trial

    # Use efficient trace types
    fig = go.Figure(
        data=go.Scattergl(  # WebGL for performance
            x=[t['number'] for t in trials],
            y=[t['value'] for t in trials],
            mode='markers'
        )
    )

    # Disable unnecessary features
    fig.update_layout(
        hovermode='closest',  # Faster than 'x' or 'y'
        dragmode='pan'        # Faster than 'zoom'
    )

    return fig
```

---

## Future Enhancements

### Planned Features

1. **Live Process Control**
   - Pause/resume optimization
   - Cancel running trials
   - Adjust parameters mid-run

2. **Advanced Visualizations**
   - Parameter importance plots
   - Hyperparameter optimization surface
   - Multi-objective Pareto front
   - 3D parameter space

3. **Multi-Study Comparison**
   - Compare multiple studies side-by-side
   - Best practices identification
   - Parameter sensitivity analysis

4. **Automated Reporting**
   - PDF report generation
   - Email notifications
   - Slack/Teams integration

5. **Custom Strategy Upload**
   - Upload strategy Python files
   - Validate strategy interface
   - Deploy to optimization

6. **Real-Time Trade Visualization**
   - Show trades on price chart
   - Entry/exit visualization
   - P&L tracking

7. **Portfolio Optimization**
   - Multi-strategy optimization
   - Portfolio allocation
   - Risk management

8. **Cloud Deployment UI**
   - AWS/GCP deployment wizard
   - Resource provisioning
   - Cost estimation

### Architecture Improvements

1. **Microservices**
   - Separate UI service
   - Separate optimization service
   - API gateway

2. **Message Queue**
   - Redis/RabbitMQ for task queuing
   - Better subprocess management
   - Distributed task execution

3. **Caching Layer**
   - Redis for result caching
   - Faster dashboard loading
   - Reduced database load

4. **Authentication**
   - User authentication
   - Role-based access control
   - Multi-tenant support

5. **API Layer**
   - RESTful API
   - GraphQL support
   - Webhook integration

---

## Appendix

### Code Examples

#### Custom Component Template

```python
# src/ui/components/my_component.py
import streamlit as st
from ..services import DatabaseService
from ..utils.validators import validate_input

def render():
    """Render my custom component"""
    st.header("My Component")

    # Input section
    user_input = st.text_input("Enter value:")

    # Validation
    is_valid, error = validate_input(user_input)
    if not is_valid:
        st.error(error)
        return

    # Processing
    result = process_data(user_input)

    # Display
    st.success(f"Result: {result}")

def process_data(data):
    """Process user data"""
    # Implementation
    return processed_data
```

#### Custom Service Template

```python
# src/ui/services/my_service.py
from sqlalchemy import create_engine
from contextlib import contextmanager

class MyService:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)

    @contextmanager
    def get_session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def my_query(self, param):
        with self.get_session() as session:
            result = session.query(...).filter(...).all()
            return result
```

### Configuration Examples

#### Streamlit Config (.streamlit/config.toml)

```toml
[server]
port = 8501
headless = false
enableCORS = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

#### Database Config Example

```python
# config/database_config.py
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    # PostgreSQL (primary)
    pg_host: str = "localhost"
    pg_port: int = 5433
    pg_database: str = "topstepb_optimization"
    pg_username: str = "postgres"
    pg_password: str = "AdminAdmin"

    # SQLite (fallback)
    sqlite_path: str = "results/optuna.db"

    # Connection pool
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600

    def get_pg_connection_string(self):
        return f"postgresql://{self.pg_username}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"

    def get_sqlite_connection_string(self):
        return f"sqlite:///{self.sqlite_path}"
```

### Testing Examples

#### Unit Test Example

```python
# tests/ui/test_validators.py
import pytest
from src.ui.utils.validators import ConfigurationValidator

def test_validate_symbol():
    validator = ConfigurationValidator()

    # Valid symbol
    is_valid, error = validator.validate_symbol("ES")
    assert is_valid
    assert error == ""

    # Invalid symbol (empty)
    is_valid, error = validator.validate_symbol("")
    assert not is_valid
    assert "required" in error.lower()

    # Invalid symbol (special chars)
    is_valid, error = validator.validate_symbol("ES@#")
    assert not is_valid
    assert "alphanumeric" in error.lower()
```

#### Integration Test Example

```python
# tests/ui/test_integration.py
import pytest
from src.ui.services import DatabaseService, PipelineService

def test_optimization_flow():
    # Setup
    db_service = DatabaseService("sqlite:///test.db")
    pipeline_service = PipelineService()

    # Build command
    config = get_test_config()
    command = pipeline_service.build_command(config)
    assert "--strategy=bollinger_squeeze" in command

    # Verify database connection
    studies = db_service.get_studies()
    assert isinstance(studies, list)
```

---

## Conclusion

This architecture document provides a comprehensive technical overview of the TopStepB Streamlit UI implementation. The design emphasizes:

- **Modularity**: Clear separation of concerns
- **Maintainability**: Well-structured codebase
- **Scalability**: Support for distributed optimization
- **Performance**: Optimized queries and rendering
- **Security**: Input validation and safe practices
- **Extensibility**: Easy to add new features

For user-facing documentation, see `UI_USER_GUIDE.md`.
For implementation details, see `logs/aggregator.log`.

---

**Document Version**: 1.0.0
**Last Updated**: October 11, 2025
**Author**: blindsipher
**Project**: TopStepB Hyperparameter Optimization Factory
