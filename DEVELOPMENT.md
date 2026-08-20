# Development Guide - Gardena Smart System Integration

This guide explains how to configure and use the development environment for the Gardena Smart System integration.

## 🚀 Quick Setup

### 1. Initial Configuration

```bash
# Complete environment setup
make setup
```

This command will:
- Create a Python virtual environment
- Install all development dependencies

### 2. Installation Verification

```bash
# Verify everything works
make help
```

## 🛠️ Development Commands

### Main Commands

| Command | Description |
|---------|-------------|
| `make help` | Shows complete help |
| `make setup` | Sets up complete environment |
| `make install` | Reinstalls dependencies |
| `make test` | Runs all tests |
| `make test-auth` | Runs authentication tests |
| `make test-real` | Real-world testing |
| `make clean` | Cleans everything (files + environment) |

### Tests

```bash
# Authentication tests only
make test-auth

# Real-world testing (requires environment variables)
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"
make test-real
```

### SSL verification

Production installs always verify TLS certificates.

`make ha-start` sets `GARDENA_DEV_MODE=true` so a local macOS Home Assistant can skip verification if the system cert store is incomplete. Do not set that variable on a real Home Assistant.

Only the exact value `true` (case-insensitive) opts out — `1`, `yes` and anything else leave verification on. When it is active, setup logs a warning so an accidental production install is visible in the log.

## 🔧 Environment Variables Configuration

### Required Variables

```bash
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"
```

### Optional Variables

```bash
export GARDENA_API_KEY="your-api-key"
```

### .env File (Recommended)

Create a `.env` file at the project root:

```bash
GARDENA_CLIENT_ID=your-client-id
GARDENA_CLIENT_SECRET=your-client-secret
GARDENA_API_KEY=your-api-key
```

Then load it:

```bash
source .env
```

## 📁 Project Structure

```
hass-gardena-smart-system/
├── custom_components/gardena_smart_system/
│   ├── __init__.py              # Main entry point
│   ├── auth.py                  # Authentication manager
│   ├── gardena_client.py        # API client
│   ├── coordinator.py           # Data coordinator
│   ├── config_flow.py           # Configuration flow
│   ├── const.py                 # Constants
│   ├── lawn_mower.py           # Mower entities
│   ├── sensor.py               # Sensor entities
│   ├── binary_sensor.py        # Binary sensor entities
│   ├── switch.py               # Switch entities
│   ├── valve.py                # Valve entities
│   ├── test_auth.py            # Authentication tests
│   ├── manifest.json           # Metadata
│   ├── strings.json            # Translations
│   └── services.yaml           # Services
├── docs/
│   └── AUTHENTICATION.md       # Authentication documentation
├── scripts/
│   └── test_auth.py            # Real-world test script
├── Makefile                    # Development commands
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── .pre-commit-config.yaml     # Pre-commit configuration
└── .gitignore                  # Ignored files
```

## 🧪 Tests

### Unit Tests

```bash
# All tests
make test

# Authentication tests only
make test-auth
```

### Real-world Testing

```bash
# Set environment variables
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"

# Test authentication
make test-real
```

### Manual Test Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest custom_components/gardena_smart_system/test_auth.py -v
```

## 🚀 Development Workflow

### 1. Daily Startup

```bash
# Check environment
make help
```

### 2. Development

```bash
# Edit code...

# Run tests
make test-auth
```

### 3. Real-world Testing

```bash
# Set environment variables
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"

# Test authentication
make test-real
```

## 🧹 Cleanup

### Complete Reset

```bash
make clean
```

This cleans:
- Python temporary files
- Test cache
- Virtual environment
- Coverage reports

## 🔧 Troubleshooting

### Common Issues

#### Virtual Environment Not Found

```bash
# Recreate environment
make setup
```

#### Missing Dependencies

```bash
# Reinstall dependencies
make install
```

#### Test Errors

```bash
# Clean and restart
make clean
make setup
make test-auth
```

### Detailed Logs

```bash
# Enable debug logs
export PYTHONPATH=.
source venv/bin/activate
python -m pytest custom_components/gardena_smart_system/test_auth.py -v -s
```

## 📚 Resources

- [Authentication Documentation](docs/AUTHENTICATION.md)
- [Gardena Smart System API v2](docs/iapi-v2.yml)
- [Home Assistant Integration Guide](https://developers.home-assistant.io/)

## 🤝 Contribution

1. Fork the project
2. Create a branch for your feature
3. Follow the development workflow
4. Add tests for your code
5. Submit a pull request

### Pre-commit Checklist

- [ ] Tests pass (`make test`)
- [ ] Authentication tests pass (`make test-auth`)
- [ ] Documentation updated if necessary 