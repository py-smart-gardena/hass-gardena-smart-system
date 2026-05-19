# Gardena Smart System Integration v2

A **complete reimplementation** of the Home Assistant integration for the Gardena Smart System, based on Gardena's v2 API.

---

If this integration keeps your garden happy, consider buying me a coffee to keep the developer happy too!

<a href="https://www.buymeacoffee.com/1vhnvriwe"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="45" alt="Buy Me A Coffee" /></a> <a href="https://paypal.me/grmklein"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" height="30" alt="PayPal" /></a>

<a href="https://www.buymeacoffee.com/1vhnvriwe"><img src="docs/bmc-qr-code.png" width="130" alt="Buy me a coffee QR code" /></a>

---

## 📡 Compatibility

This integration **only works with WiFi-enabled Gardena Smart System devices that connect through a Gardena Smart Gateway**. It communicates with the Gardena cloud API, which requires the gateway as a bridge.

**Not compatible with:**
- Bluetooth-only Gardena devices (e.g. older mowers, Gardena Bluetooth sensors)
- Devices that connect directly via Bluetooth to a phone without a gateway

If your device does not require a Gardena Smart Gateway for operation, it is not supported by this integration.

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

## 🧪 Testing Status

### ✅ Tested and Working

- **Lawn Mower** (`lawn_mower`) : ✅ Fully tested and functional
  - Start/pause/dock controls working
  - Real-time status updates via WebSocket
  - Custom service buttons operational
- **Smart Irrigation Control** (`valve`) : ✅ Fully tested and functional
  - Multiple valve control (6 valves detected)
  - Open/close operations working
  - Real-time status updates
- **Power Socket** (`switch`) : ✅ Fully tested and functional
  - On/off control working
  - Real-time status updates

### ⚠️ Not Yet Tested

- **Water Control** (`valve`) : ⚠️ Implementation complete but not tested
  - Single valve control implementation ready
  - Needs real device testing
- **Sensors** (`sensor`) : ⚠️ Implementation complete but not tested
  - Temperature, humidity, light sensors
  - Soil sensors implementation ready
  - Needs real device testing

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

#### Mower error sensor

The `mower_error` sensor exposes the `last_error_code` field from the Gardena API. To avoid false positives in error-notification automations, **informational operational states are filtered** and reported as `no_message` instead:

| Code filtered | Meaning |
|---|---|
| `parked_daily_limit_reached` | Daily mowing limit reached — normal operation |
| `outside_working_area` | Mower returned outside its zone — normal |
| `off_disabled` | Disabled manually by user |
| `off_hatch_open` | Hatch opened for maintenance |
| `off_hatch_closed` | Hatch closed — normal state |
| `wait_updating` | Firmware update in progress |
| `wait_power_up` | Booting up |
| `wait_stop_pressed` | Stop button held — user maintenance |
| `wait_for_safety_pin` | Waiting for safety pin — user maintenance |
| `guide_calibration_accomplished` | Calibration completed successfully |
| `connection_changed` | Network state change — informational |
| `connection_not_changed` | Network state change — informational |
| `uninitialised` | Normal boot state |

This means a simple automation like `state != 'no_message'` reliably catches only real errors that require attention.

## 🔧 Available Services

The integration provides several services that can be called from automations, scripts, or the Developer Tools. All services require a `device_id` parameter.

### 🚜 Lawn Mower Services

#### `gardena_smart_system.mower_start`
Start automatic mowing (follows the device's schedule).

**Parameters:**
- `device_id` (required): The device ID of the lawn mower

**Example:**
```yaml
service: gardena_smart_system.mower_start
data:
  device_id: "your_mower_device_id"
```

#### `gardena_smart_system.mower_start_manual`
Start manual mowing for a specified duration.

**Parameters:**
- `device_id` (required): The device ID of the lawn mower
- `duration` (optional): Duration in seconds (60-14400, default: 1800)

**Example:**
```yaml
service: gardena_smart_system.mower_start_manual
data:
  device_id: "your_mower_device_id"
  duration: 3600  # 1 hour
```

#### `gardena_smart_system.mower_park`
Park the mower until the next scheduled task.

**Parameters:**
- `device_id` (required): The device ID of the lawn mower

**Example:**
```yaml
service: gardena_smart_system.mower_park
data:
  device_id: "your_mower_device_id"
```

#### `gardena_smart_system.mower_park_until_notice`
Park the mower until further notice (ignores schedule).

**Parameters:**
- `device_id` (required): The device ID of the lawn mower

**Example:**
```yaml
service: gardena_smart_system.mower_park_until_notice
data:
  device_id: "your_mower_device_id"
```

### 🔌 Power Socket Services

#### `gardena_smart_system.power_socket_on`
Turn on the power socket for a specified duration.

**Parameters:**
- `device_id` (required): The device ID of the power socket
- `duration` (optional): Duration in seconds (60-86400, default: 3600)

**Example:**
```yaml
service: gardena_smart_system.power_socket_on
data:
  device_id: "your_power_socket_device_id"
  duration: 7200  # 2 hours
```

#### `gardena_smart_system.power_socket_on_indefinite`
Turn on the power socket indefinitely.

**Parameters:**
- `device_id` (required): The device ID of the power socket

**Example:**
```yaml
service: gardena_smart_system.power_socket_on_indefinite
data:
  device_id: "your_power_socket_device_id"
```

#### `gardena_smart_system.power_socket_off`
Turn off the power socket immediately.

**Parameters:**
- `device_id` (required): The device ID of the power socket

**Example:**
```yaml
service: gardena_smart_system.power_socket_off
data:
  device_id: "your_power_socket_device_id"
```

#### `gardena_smart_system.power_socket_pause`
Pause automatic operation of the power socket.

**Parameters:**
- `device_id` (required): The device ID of the power socket

**Example:**
```yaml
service: gardena_smart_system.power_socket_pause
data:
  device_id: "your_power_socket_device_id"
```

#### `gardena_smart_system.power_socket_unpause`
Resume automatic operation of the power socket.

**Parameters:**
- `device_id` (required): The device ID of the power socket

**Example:**
```yaml
service: gardena_smart_system.power_socket_unpause
data:
  device_id: "your_power_socket_device_id"
```

### 🚰 Valve Services

#### `gardena_smart_system.valve_open`
Open the valve for a specified duration.

**Parameters:**
- `device_id` (required): The device ID of the valve
- `duration` (optional): Duration in seconds (60-14400, default: 3600)

**Example:**
```yaml
service: gardena_smart_system.valve_open
data:
  device_id: "your_valve_device_id"
  duration: 1800  # 30 minutes
```

#### `gardena_smart_system.valve_close`
Close the valve immediately.

**Parameters:**
- `device_id` (required): The device ID of the valve

**Example:**
```yaml
service: gardena_smart_system.valve_close
data:
  device_id: "your_valve_device_id"
```

#### `gardena_smart_system.valve_pause`
Pause automatic operation of the valve.

**Parameters:**
- `device_id` (required): The device ID of the valve

**Example:**
```yaml
service: gardena_smart_system.valve_pause
data:
  device_id: "your_valve_device_id"
```

#### `gardena_smart_system.valve_unpause`
Resume automatic operation of the valve.

**Parameters:**
- `device_id` (required): The device ID of the valve

**Example:**
```yaml
service: gardena_smart_system.valve_unpause
data:
  device_id: "your_valve_device_id"
```

### 🌐 WebSocket Services

#### `gardena_smart_system.reconnect_websocket`
Force reconnection of the WebSocket connection.

**Parameters:** None

**Example:**
```yaml
service: gardena_smart_system.reconnect_websocket
```

### 📋 System Services

#### `gardena_smart_system.reload`
Reload the Gardena Smart System integration.

**Parameters:** None

**Example:**
```yaml
service: gardena_smart_system.reload
```

#### `gardena_smart_system.websocket_diagnostics`
Get WebSocket connection diagnostics and status information.

**Parameters:**
- `detailed` (optional): Include detailed connection information (default: false)

**Example:**
```yaml
service: gardena_smart_system.websocket_diagnostics
data:
  detailed: true
```

### 🔍 Finding Device IDs

To find the device ID for a specific device:

1. Go to **Developer Tools** > **States**
2. Search for your device (e.g., "mower", "valve", "switch")
3. Look for the `device_id` attribute in the entity state
4. Or check the entity's unique ID (usually contains the device ID)

**Example entity state:**
```yaml
device_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

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

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full list of changes, fixes, and breaking changes per version.

## 🔗 Useful Links

- [Gardena Smart System API v2](https://developer.husqvarnagroup.cloud/)
- [Home Assistant Documentation](https://developers.home-assistant.io/)
- [Integration Guide](https://developers.home-assistant.io/docs/creating_integration_manifest/) 
