## Overview

`RFID Agent` is an IoT application designed to connect web and native applications with the RFID device model SF5004, SGI0901, ... This project leverages Mosquitto MQTT for seamless communication between the RFID device and client applications.

## Technologies Used

- **Programming Language**: Python
- **Dependencies**:
  - `paho-mqtt` for MQTT communication
  - `uhfReaderApi` for RFID reader communication

## Key Features

- Connect and interact with the RFID device model SF5004.
- Publish and subscribe to RFID events using Mosquitto MQTT.
- Store and manage RFID data in a database.
- Provide a web-based interface for monitoring and configuration.
- Support for real-time RFID event handling.

## Installation & Configuration

1. Clone the repository:
   ```pwsh
   git clone https://github.com/your-username/py-rfid-agent.git
   cd py-rfid-agent
   ```
2. Set up a virtual environment:
   ```pwsh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:

   ```pwsh
   pip install -r requirements.txt
   ```

4. Download and install Mosquitto MQTT following below instruction

   4.1 Download Mosquitto from [here](https://mosquitto.org/download/)

   4.2 Get you device IPv4 type A

   ```pwsh
   ipconfig
   -----------------------------------------------------------------
   Ethernet adapter:

   Connection-specific DNS Suffix  . :
   Link-local IPv6 Address . . . . . : xxxx::xxxx:xxxx:xxxx:xxxx%6
   IPv4 Address. . . . . . . . . . . : 10.xx.xxx.xx   # Copy this one
   Subnet Mask . . . . . . . . . . . : 255.xxx.xxx.x
   IPv4 Address. . . . . . . . . . . : 192.xxx.x.xx
   Subnet Mask . . . . . . . . . . . : 255.xxx.xxx.xxx
   Default Gateway . . . . . . . . . : 10.xx.xxx.xxx

   ```

   4.3 Update Mosquitto config:

   Open the folder that you have installed Mosquitto in. Open `mosquitto.conf` and update the configuration like this:

   ```conf
   # MQTT TCP for publisher/subscriber/backend
   listener 1883 <IPv4 Address>

   # MQTT WebSocket for client
   listener 9001 <IPv4 Address>
   protocol websockets
   ```

   4.4 Restart Mosquitto service

   ```pwsh
   net stop mosquitto
   net start mosquitto
   ```

5. Run the application:
   ```pwsh
   python main.py
   ```

## Testing

### Running Tests

This project includes comprehensive test coverage for all modules. To run tests:

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test files
python -m pytest tests/test_main.py
python -m pytest tests/helpers/
python -m pytest tests/decorators/

# Run tests with different verbosity
python -m pytest -v                    # verbose
python -m pytest -q                    # quiet
python -m pytest -x                    # stop on first failure
```

### Test Categories

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **Mock Tests**: Test with mocked MQTT and TCP connections

### Pre-commit Testing

Use the provided scripts to run all checks before committing:

```bash
# Linux/macOS
./scripts/test.sh

# Windows
scripts\test.bat
```

### Continuous Integration

Tests run automatically on GitHub Actions for:

- Python 3.10, 3.11, 3.12
- Multiple operating systems (Ubuntu, Windows, macOS)
- Code quality checks (flake8, mypy)
- Security scans (bandit, safety)
- Coverage reporting

## Development

### Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning

Install development dependencies:

```bash
pip install black isort flake8 mypy bandit safety coverage-badge
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
pip install pre-commit
pre-commit install
```

## Building Executable

Create standalone executables for distribution:

### Windows

```batch
scripts\build.bat
```

### Linux/macOS

```bash
# Make script executable (one time)
chmod +x scripts/build.sh

# Build application
./scripts/build.sh
```

All build scripts create a `dist/RFID Agent/` directory containing the complete application with all dependencies.

For more details, see [scripts/README.md](scripts/README.md).

## Contribution

Feel free to fork this repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
