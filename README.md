<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Gardena Smart System Integration v2.0.0](#gardena-smart-system-integration-v200)
  - [⚠️ Important: Complete Reimplementation](#-important-complete-reimplementation)
    - [Why a Complete Reimplementation?](#why-a-complete-reimplementation)
  - [🚀 v2 New Features](#-v2-new-features)
  - [📋 Features](#-features)
    - [Supported Entities](#supported-entities)
    - [Lawn Mower Features](#lawn-mower-features)
  - [🛠️ Installation](#-installation)
    - [⚠️ Important: Clean Installation Required](#-important-clean-installation-required)
    - [Manual Installation](#manual-installation)
    - [Configuration](#configuration)
  - [🔧 Technical Architecture](#-technical-architecture)
    - [File Structure](#file-structure)
    - [Main Components](#main-components)
      - [Coordinator (`coordinator.py`)](#coordinator-coordinatorpy)
      - [API Client (`gardena_client.py`)](#api-client-gardena_clientpy)
      - [Entities](#entities)
  - [🧪 Tests](#-tests)
    - [Running Tests](#running-tests)
    - [Available Tests](#available-tests)
  - [🔄 Migration from Previous Versions](#-migration-from-previous-versions)
    - [⚠️ Migration Required](#-migration-required)
    - [What Changes?](#what-changes)
    - [Migration Checklist](#migration-checklist)
  - [🐛 Troubleshooting](#-troubleshooting)
    - [Common Issues](#common-issues)
    - [Logs](#logs)
  - [🤝 Contribution](#-contribution)
  - [📄 License](#-license)
  - [🔗 Useful Links](#-useful-links)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Gardena Smart System Integration v2.0.0

A **complete reimplementation** of the Home Assistant integration for the Gardena Smart System, based on Gardena's v2 API.

## ⚠️ Important: Complete Reimplementation

This is a **complete rewrite** of the Gardena Smart System integration. It is **strongly recommended** to:

1. **Remove the existing integration** from Home Assistant
2. **Restart Home Assistant**
3. **Re-add the integration** with this new version

This ensures a clean installation and prevents any conflicts between the old and new implementations.

### Why a Complete Reimplementation?

- **New API v2**: Uses Gardena's completely new API architecture
- **Modern Framework**: Built using the latest Home Assistant integration patterns
- **Improved Architecture**: Better state management and error handling
- **Enhanced Features**: More reliable device detection and control

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

### ⚠️ Important: Clean Installation Required

**Before installing this new version, you must remove the existing Gardena Smart System integration:**

1. Go to **Configuration** > **Integrations**
2. Find **Gardena Smart System** in the list
3. Click on it and select **Delete**
4. Confirm the deletion
5. **Restart Home Assistant**

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

## 🔄 Migration from Previous Versions

### ⚠️ Migration Required

This is a **complete reimplementation** and requires a full migration:

1. **Remove the existing integration** from Home Assistant
2. **Restart Home Assistant**
3. **Install this new version**
4. **Re-add the integration** with your API credentials

### What Changes?

- **New entity IDs**: All entities will have new unique IDs
- **New device structure**: Devices are now organized differently
- **Enhanced features**: Better device detection and control
- **Improved reliability**: More stable connection and state management

### Migration Checklist

- [ ] Remove existing Gardena Smart System integration
- [ ] Restart Home Assistant
- [ ] Install new integration files
- [ ] Re-add integration with API credentials
- [ ] Verify all devices are detected
- [ ] Update any automations or scripts that reference old entity IDs

## 🐛 Troubleshooting

### Common Issues

**Authentication Error**
- Check your API credentials
- Make sure your account has access to the v2 API

**No Devices Detected**
- Check that your devices are connected to the Smart System
- Make sure they are visible in the Gardena app
- **Ensure you've removed the old integration first**

**Entities Not Available**
- Check internet connection
- Check Home Assistant logs for more details
- **Verify you've restarted Home Assistant after removing the old integration**

**Duplicate Entities or Conflicts**
- **This usually happens when the old integration wasn't properly removed**
- Remove the integration completely and restart Home Assistant
- Re-add the integration fresh

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