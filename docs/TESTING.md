# Testing Documentation for RFID Agent

## Overview

This document provides comprehensive information about the testing setup for the RFID Agent project.

## Test Coverage Summary

- **Total Tests**: 101 tests
- **Coverage**: 99.54%
- **Test Categories**:
  - Unit Tests: 78 tests
  - Integration Tests: 23 tests

## Test Structure

```
tests/
├── decorators/
│   └── test_throttle.py           # 22 tests - Throttle decorator functionality
├── helpers/
│   ├── test_configuration.py      # 18 tests - Configuration management
│   └── test_ipv4.py              # 13 tests - IPv4 utility functions
└── test_main.py                  # 48 tests - Main Application class
```

## GitHub Actions Workflows

### 1. Main CI/CD Pipeline (`ci.yaml`)

Triggers on: Push to `main`, `develop`, `feat/*` branches and PRs

**Jobs:**

- **Test Matrix**: Python 3.10, 3.11, 3.12 on Ubuntu
- **Security Scan**: Bandit and Safety checks
- **Build**: Cross-platform executables (Windows, Linux, macOS)
- **Release**: Automated releases on main branch
- **Notifications**: Success/failure notifications

**Features:**

- Dependency caching
- Code quality checks (flake8, mypy)
- Coverage reporting with Codecov
- Security vulnerability scanning
- Multi-platform executable building
- Automated releases

### 2. Quick Test Pipeline (`test.yaml`)

Triggers on: Push to `feat/*`, `hotfix/*` branches and PRs

**Features:**

- Fast feedback for development
- Essential tests only
- Python 3.12 on Ubuntu
- Basic linting checks

## Local Development

### Prerequisites

```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio
pip install black isort flake8 mypy bandit safety
```

### Running Tests

```bash
# All tests with coverage
python -m pytest

# Specific test categories
python -m pytest tests/test_main.py           # Application tests
python -m pytest tests/helpers/               # Helper function tests
python -m pytest tests/decorators/            # Decorator tests

# With different options
python -m pytest -v                           # Verbose output
python -m pytest -x                           # Stop on first failure
python -m pytest --cov-report=html            # HTML coverage report
python -m pytest -m "not slow"                # Skip slow tests
```

### Pre-commit Setup

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

This will automatically run:

- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Tests (pytest)

### Local Testing Scripts

Use the provided scripts for comprehensive testing:

**Windows:**

```cmd
scripts\test.bat
```

**Linux/macOS:**

```bash
./scripts/test.sh
```

These scripts run:

1. Code formatting checks
2. Import sorting verification
3. Linting
4. Type checking
5. Full test suite with coverage
6. Security scanning

## Test Categories and Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.network` - Tests requiring network access

## Mocking Strategy

The tests extensively use mocking for:

### MQTT Client Mocking

- `paho.mqtt.client.Client` - Mock MQTT connections
- Connection callbacks and message handling
- Publish/subscribe operations

### UHF Reader Mocking

- `uhf.reader.GClient` - Mock TCP connections to RFID reader
- EPC data simulation
- Reader configuration testing

### File System Mocking

- Configuration file operations
- Temporary file creation for testing
- Path manipulation testing

## Coverage Targets

- **Overall Coverage**: 99.54% (Target: >85%)
- **Individual Modules**:
  - `main.py`: 99% (Only main execution block excluded)
  - `helpers/`: 100%
  - `decorators/`: 100%
  - `constants/`: 100%

## Continuous Integration Features

### Code Quality Gates

- **Linting**: flake8 with custom rules
- **Type Checking**: mypy with strict settings
- **Security**: bandit for security issues
- **Dependencies**: safety for vulnerability scanning

### Build Matrix

- **Python Versions**: 3.10, 3.11, 3.12
- **Operating Systems**: Ubuntu (tests), Windows/macOS (builds)
- **Parallel Execution**: Tests run in parallel where possible

### Artifacts

- Test coverage reports (HTML)
- Security scan results (JSON)
- Cross-platform executables
- Coverage badges

## Best Practices Enforced

1. **Code Style**: Black formatting, consistent imports
2. **Type Safety**: mypy type checking
3. **Security**: Regular vulnerability scans
4. **Documentation**: Comprehensive docstrings and comments
5. **Error Handling**: Proper exception testing
6. **Performance**: Throttling and async/await testing

## Integration with Development Workflow

1. **Feature Development**: Use `feat/*` branches with quick tests
2. **Pull Requests**: Full CI pipeline runs on PRs
3. **Main Branch**: Complete pipeline with releases
4. **Issue Templates**: Structured bug reports and features
5. **PR Templates**: Comprehensive review checklists

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Path Issues**: Use absolute paths in tests
3. **Async Tests**: Use `@pytest.mark.asyncio` decorator
4. **Mock Conflicts**: Reset mocks between tests

### Debugging Tests

```bash
# Run with debugging
python -m pytest --pdb                        # Drop into debugger on failure
python -m pytest -s                           # Don't capture stdout
python -m pytest --tb=long                    # Full traceback
python -m pytest -k "test_name"               # Run specific test
```

## Future Enhancements

1. **Performance Testing**: Add load testing for MQTT/TCP connections
2. **Hardware-in-Loop**: Integration with actual RFID hardware
3. **End-to-End Testing**: Complete workflow testing
4. **Visual Testing**: Screenshot comparison for UI components
5. **API Testing**: REST API endpoint testing if added
