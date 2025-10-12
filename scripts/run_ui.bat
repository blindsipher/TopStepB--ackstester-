@echo off
REM TopStepB Backtester UI Launcher
REM Launches the Streamlit web interface

echo ================================================
echo  TopStepB Backtester - Web UI
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check PostgreSQL service
echo Checking PostgreSQL service...
sc query postgresql-x64-18 | find "RUNNING" >nul
if errorlevel 1 (
    echo WARNING: PostgreSQL 18 is not running
    echo Attempting to start service...
    net start postgresql-x64-18 2>nul
    if errorlevel 1 (
        echo WARNING: Could not start PostgreSQL service
        echo The UI will work but optimization history may not be available
    ) else (
        echo [OK] PostgreSQL service started
    )
) else (
    echo [OK] PostgreSQL is running
)
echo.

REM Navigate to project directory
cd /d "%~dp0.."

REM Install dependencies if needed
echo Checking dependencies...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Installing Streamlit dependencies...
    python -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
)
echo.

REM Set environment variables
set STREAMLIT_SERVER_PORT=8501
set STREAMLIT_SERVER_ADDRESS=localhost
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

REM Launch Streamlit
echo ================================================
echo  Starting TopStepB Web UI
echo ================================================
echo.
echo Opening browser at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

python -m streamlit run src\ui\app.py

pause
