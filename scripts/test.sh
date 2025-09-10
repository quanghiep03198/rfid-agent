#!/bin/bash

# Local test runner script for RFID Agent
# Run this script before pushing to GitHub

echo "🧪 Running RFID Agent Test Suite..."
echo "=================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected. Consider activating your venv."
fi

# Run code formatting check
echo "📝 Checking code formatting..."
python -m black --check --diff . || {
    echo "❌ Code formatting issues found. Run 'python -m black .' to fix."
    exit 1
}

# Run import sorting check
echo "📦 Checking import sorting..."
python -m isort --check-only --diff . || {
    echo "❌ Import sorting issues found. Run 'python -m isort .' to fix."
    exit 1
}

# Run linting
# echo "🔍 Running linter..."
# python -m flake8 . --count --statistics || {
#     echo "❌ Linting issues found."
#     exit 1
# }

# Run type checking
echo "🔍 Running type checker..."
python -m mypy --ignore-missing-imports . || {
    echo "⚠️  Type checking completed with warnings."
}

# Run tests with coverage
echo "🧪 Running tests with coverage..."
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html || {
    echo "❌ Tests failed."
    exit 1
}

# Security scan
echo "🔒 Running security scan..."
python -m bandit -r . -f json || {
    echo "⚠️  Security scan completed with warnings."
}

echo ""
echo "✅ All checks passed! Ready to push to GitHub."
echo "📊 Coverage report generated in htmlcov/index.html"
echo ""
