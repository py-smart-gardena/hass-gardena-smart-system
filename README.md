# Gardena Smart System Integration v2.0.0

A modern Home Assistant integration for the Gardena Smart System, based on Gardena's v2 API.

## 🚀 v2 New Features

- **Modern Architecture** : Uses Home Assistant recommended patterns
- **Standardized Framework** : Based on the official integration framework
- **Python 3.11+** : Support for recent Python versions
- **API v2** : Uses the new Gardena Smart System API
- **Centralized State Management** : Coordinator for data synchronization
- **Automated Tests** : Unit tests with mocks

## 📋 Features

### Supported Entities

- **Lawn Mowers** (`lawn_mower`) : Control of automatic lawn mowers
- **Sensors** (`sensor`) : Temperature, humidity sensors, etc.
- **Binary Sensors** (`binary_sensor`) : Online/offline status
- **Switches** (`switch`) : Smart power sockets
- **Valves** (`valve`) : Irrigation valves

### Lawn Mower Features

- Start mowing
- Pause
- Return to charging station
- State and activity monitoring

## 🛠️ Installation

### Manual Installation

1. Copy the `custom_components/gardena_smart_system` folder to your `config/custom_components/` folder
2. Restart Home Assistant
3. Go to **Configuration** > **Integrations**
4. Click **+ Add Integration**
5. Search for **Gardena Smart System**
6. Enter your API credentials

### Configuration

You will need:
- **Client ID** : Your Gardena application key
- **Client Secret** : Your Gardena application secret

These credentials can be obtained through the [Gardena Developer Portal](https://developer.husqvarnagroup.cloud/).

## 🔧 Technical Architecture

### File Structure

```
custom_components/gardena_smart_system/
├── __init__.py              # Main entry point
├── config_flow.py           # UI configuration flow
├── const.py                 # Integration constants
├── coordinator.py           # Data coordinator
├── gardena_client.py        # Gardena API client
├── lawn_mower.py           # Lawn mower entities
├── sensor.py               # Sensor entities
├── binary_sensor.py        # Binary sensor entities
├── switch.py               # Switch entities
├── valve.py                # Valve entities
├── manifest.json           # Integration metadata
├── strings.json            # Translation strings
├── services.yaml           # Custom services
└── translations/           # Translations
```

### Main Components

#### Coordinator (`coordinator.py`)
- Manages data synchronization with the API
- Automatically updates entities
- Handles errors and reconnection

#### API Client (`gardena_client.py`)
- Communication with Gardena v2 API
- OAuth2 authentication
- HTTP request management

#### Entities
- Each device type has its own entity
- Uses modern Home Assistant patterns
- Supports specific features

## 🧪 Tests

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest custom_components/gardena_smart_system/test_init.py -v
```

### Available Tests

- **Configuration** : Configuration flow test
- **Authentication** : Invalid credentials test
- **Installation** : Integration installation test
- **Uninstallation** : Integration uninstallation test

## 🔄 Update

To update to v2:

1. Backup your current configuration
2. Uninstall the old version
3. Install the new version
4. Reconfigure the integration

## 🐛 Troubleshooting

### Common Issues

**Authentication Error**
- Check your API credentials
- Make sure your account has access to the v2 API

**No Devices Detected**
- Check that your devices are connected to the Smart System
- Make sure they are visible in the Gardena app

**Entities Not Available**
- Check internet connection
- Check Home Assistant logs for more details

### Logs

Enable detailed logs in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.gardena_smart_system: debug
```

## 🤝 Contribution

Contributions are welcome! To contribute:

1. Fork the project
2. Create a branch for your feature
3. Add tests for your code
4. Submit a pull request

## 📄 License

This project is under MIT license. See the `LICENSE` file for more details.

## 🔗 Useful Links

- [Gardena Smart System API v2](https://developer.husqvarnagroup.cloud/)
- [Home Assistant Documentation](https://developers.home-assistant.io/)
- [Integration Guide](https://developers.home-assistant.io/docs/creating_integration_manifest/) 