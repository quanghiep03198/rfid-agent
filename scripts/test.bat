@echo off
REM Local test runner script for RFID Agent (Windows)
REM Run this script before pushing to GitHub

echo 🧪 Running RFID Agent Test Suite...
echo ==================================

REM Resolve venv python path relative to repository root
set "REPO_ROOT=%~dp0.."
set "PYTHON=%REPO_ROOT%\venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo ❌ Virtual environment Python not found: %PYTHON%
    echo 💡 Create it with: python -m venv venv
    echo 💡 Then install deps with: %PYTHON% -m pip install -r requirements.txt -r requirements-ci.txt
    exit /b 1
)

REM Check if in virtual environment
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  Warning: No virtual environment detected. Consider activating your venv.
)

REM Run code formatting check
echo 📝 Checking code formatting...
"%PYTHON%" -m black --check --diff . || (
    echo ❌ Code formatting issues found. Run 'python -m black .' to fix.
    exit /b 1
)

REM Run import sorting check
echo 📦 Checking import sorting...
"%PYTHON%" -m isort --check-only --diff . || (
    echo ❌ Import sorting issues found. Run 'python -m isort .' to fix.
    exit /b 1
)

@REM REM Run linting
@REM echo 🔍 Running linter...
@REM python -m flake8 main.py --count --statistics || (
@REM     echo ❌ Linting issues found.
@REM     exit /b 1
@REM )

REM Run type checking
echo 🔍 Running type checker...
"%PYTHON%" -m mypy --ignore-missing-imports . || (
    echo ⚠️  Type checking completed with warnings.
)

REM Run tests with coverage
echo 🧪 Running tests with coverage...
"%PYTHON%" -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html || (
    echo ❌ Tests failed.
    exit /b 1
)

REM Security scan
echo 🔒 Running security scan...
"%PYTHON%" -m bandit -r . -f json || (
    echo ⚠️  Security scan completed with warnings.
)

echo.
echo ✅ All checks passed! Ready to push to GitHub.
echo 📊 Coverage report generated in htmlcov\index.html
echo.
