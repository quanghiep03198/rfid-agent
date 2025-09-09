@echo off
REM Local test runner script for RFID Agent (Windows)
REM Run this script before pushing to GitHub

echo 🧪 Running RFID Agent Test Suite...
echo ==================================

REM Check if in virtual environment
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  Warning: No virtual environment detected. Consider activating your venv.
)

REM Run code formatting check
echo 📝 Checking code formatting...
python -m black --check --diff . || (
    echo ❌ Code formatting issues found. Run 'python -m black .' to fix.
    exit /b 1
)

REM Run import sorting check
echo 📦 Checking import sorting...
python -m isort --check-only --diff . || (
    echo ❌ Import sorting issues found. Run 'python -m isort .' to fix.
    exit /b 1
)

REM Run linting
echo 🔍 Running linter...
python -m flake8 main.py --count --statistics || (
    echo ❌ Linting issues found.
    exit /b 1
)

REM Run type checking
echo 🔍 Running type checker...
python -m mypy --ignore-missing-imports . || (
    echo ⚠️  Type checking completed with warnings.
)

REM Run tests with coverage
echo 🧪 Running tests with coverage...
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html || (
    echo ❌ Tests failed.
    exit /b 1
)

REM Security scan
echo 🔒 Running security scan...
python -m bandit -r . -f json || (
    echo ⚠️  Security scan completed with warnings.
)

echo.
echo ✅ All checks passed! Ready to push to GitHub.
echo 📊 Coverage report generated in htmlcov\index.html
echo.
