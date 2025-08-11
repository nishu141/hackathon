@echo off
chcp 65001 >nul
echo 🚀 Telecom AI LangGraph Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✓ Python detected
echo.

REM Check if we're in the right directory
if not exist "telecom_ai_langgraph.py" (
    echo ❌ Error: telecom_ai_langgraph.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo ✓ Project files found
echo.

REM Run the Python launcher
echo 🔧 Starting dependency management and application...
echo.
python run_telecom_ai.py

if errorlevel 1 (
    echo.
    echo ❌ Application failed to run
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ✅ Application completed successfully
pause
