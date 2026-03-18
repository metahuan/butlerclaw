@echo off
REM Quick setup script for Butlerclaw development environment (Windows)
REM Usage: scripts\setup.bat

echo 🚀 Setting up Butlerclaw development environment...

REM Check Python version
echo 📋 Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version') do set PYTHON_VERSION=%%a
echo   Found Python %PYTHON_VERSION%

REM Check if Python 3.8+
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.8 or higher is required
    exit /b 1
)
echo ✓ Python version is compatible

REM Check for tkinter
echo 📋 Checking tkinter...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo ❌ tkinter is not installed
    echo Please reinstall Python and check "tcl/tk and IDLE" option
    exit /b 1
)
echo ✓ tkinter is available

REM Create virtual environment
echo 📦 Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
pip install --upgrade pip -q

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt -q
echo ✓ Dependencies installed

REM Install development dependencies
echo 📥 Installing development dependencies...
pip install -r requirements-dev.txt -q
echo ✓ Development dependencies installed

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    (
        echo # Butlerclaw Development Environment
        echo DEBUG=true
        echo LOG_LEVEL=debug
    ) > .env
    echo ✓ .env file created
)

echo.
echo ✅ Setup complete!
echo.
echo Next steps:
echo   1. Virtual environment is already activated
echo   2. Run the application: python openclaw_assistant.py
echo   3. Run tests: pytest tests/
echo.

pause
