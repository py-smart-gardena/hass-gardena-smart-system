# Gardena Smart System Services

This document describes the Home Assistant services available for controlling Gardena Smart System devices.

## Overview

The Gardena Smart System integration provides a comprehensive set of services that allow you to control your Gardena devices directly from Home Assistant. These services are automatically registered when the integration is loaded and can be called from automations, scripts, or the Developer Tools.

## Available Services

### Mower Services

#### `gardena_smart_system.mower_start`
Start automatic mowing according to the device's schedule.

**Service Data:**
```yaml
device_id: "your-mower-device-id"
duration: 1800  # Optional, default: 1800 seconds (30 minutes)
```

**Example:**
```yaml
service: gardena_smart_system.mower_start
data:
  device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
```

#### `gardena_smart_system.mower_start_manual`
Start manual mowing for a specified duration.

**Service Data:**
```yaml
device_id: "your-mower-device-id"
duration: 1800  # Required, 60-14400 seconds (1 minute to 4 hours)
```

**Example:**
```yaml
service: gardena_smart_system.mower_start_manual
data:
  device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
  duration: 3600  # 1 hour
```

#### `gardena_smart_system.mower_park`
Park the mower until the next scheduled task.

**Service Data:**
```yaml
device_id: "your-mower-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.mower_park
data:
  device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
```

#### `gardena_smart_system.mower_park_until_notice`
Park the mower and ignore the schedule until further notice.

**Service Data:**
```yaml
device_id: "your-mower-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.mower_park_until_notice
data:
  device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
```

### Power Socket Services

#### `gardena_smart_system.power_socket_on`
Turn on a power socket for a specified duration.

**Service Data:**
```yaml
device_id: "your-power-socket-device-id"
duration: 3600  # Optional, default: 3600 seconds (1 hour), 60-86400 seconds
```

**Example:**
```yaml
service: gardena_smart_system.power_socket_on
data:
  device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
  duration: 7200  # 2 hours
```

#### `gardena_smart_system.power_socket_on_indefinite`
Turn on a power socket indefinitely (until manually turned off).

**Service Data:**
```yaml
device_id: "your-power-socket-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.power_socket_on_indefinite
data:
  device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

#### `gardena_smart_system.power_socket_off`
Turn off a power socket immediately.

**Service Data:**
```yaml
device_id: "your-power-socket-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.power_socket_off
data:
  device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

#### `gardena_smart_system.power_socket_pause`
Pause automatic operation of a power socket.

**Service Data:**
```yaml
device_id: "your-power-socket-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.power_socket_pause
data:
  device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

#### `gardena_smart_system.power_socket_unpause`
Resume automatic operation of a power socket.

**Service Data:**
```yaml
device_id: "your-power-socket-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.power_socket_unpause
data:
  device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

### Valve Services

#### `gardena_smart_system.valve_open`
Open a valve for a specified duration.

**Service Data:**
```yaml
device_id: "your-valve-device-id"
duration: 3600  # Optional, default: 3600 seconds (1 hour), 60-14400 seconds
```

**Example:**
```yaml
service: gardena_smart_system.valve_open
data:
  device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
  duration: 1800  # 30 minutes
```

#### `gardena_smart_system.valve_close`
Close a valve immediately.

**Service Data:**
```yaml
device_id: "your-valve-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.valve_close
data:
  device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
```

#### `gardena_smart_system.valve_pause`
Pause automatic operation of a valve.

**Service Data:**
```yaml
device_id: "your-valve-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.valve_pause
data:
  device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
```

#### `gardena_smart_system.valve_unpause`
Resume automatic operation of a valve.

**Service Data:**
```yaml
device_id: "your-valve-device-id"
```

**Example:**
```yaml
service: gardena_smart_system.valve_unpause
data:
  device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
```

## Finding Device IDs

To find the device ID for a specific device:

1. Go to **Settings** > **Devices & Services**
2. Find your Gardena Smart System integration
3. Click on the integration to see all devices
4. Click on a specific device to see its details
5. The device ID is shown in the device information

Alternatively, you can use the Developer Tools:

1. Go to **Developer Tools** > **States**
2. Search for `gardena_smart_system`
3. Look for entities like `lawn_mower.sileno` or `switch.power_socket_1`
4. The device ID is part of the entity's unique ID

## Automation Examples

### Start Mowing When Weather is Good

```yaml
automation:
  - alias: "Start mowing on good weather"
    trigger:
      platform: state
      entity_id: sensor.weather_condition
      to: "sunny"
    condition:
      - condition: time
        after: "09:00:00"
        before: "18:00:00"
    action:
      - service: gardena_smart_system.mower_start
        data:
          device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
```

### Water Garden in the Morning

```yaml
automation:
  - alias: "Water garden in the morning"
    trigger:
      platform: time
      at: "06:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.soil_humidity
        below: 30
    action:
      - service: gardena_smart_system.valve_open
        data:
          device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
          duration: 1800  # 30 minutes
```

### Turn Off Garden Lights at Dawn

```yaml
automation:
  - alias: "Turn off garden lights at dawn"
    trigger:
      platform: sun
      event: sunrise
    action:
      - service: gardena_smart_system.power_socket_off
        data:
          device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

### Emergency Stop All Devices

```yaml
automation:
  - alias: "Emergency stop all devices"
    trigger:
      platform: event
      event_type: gardena_emergency_stop
    action:
      - service: gardena_smart_system.mower_park_until_notice
        data:
          device_id: "4ad7d828-b19f-47d5-b7d2-15eea0fb8516"
      - service: gardena_smart_system.valve_close
        data:
          device_id: "14ff41a6-21eb-454f-b3ad-51f0958c0365"
      - service: gardena_smart_system.power_socket_off
        data:
          device_id: "31c6c096-bf0e-4c1b-a8b6-69b21c79828a"
```

## Error Handling

The services include comprehensive error handling:

- **400 Bad Request**: Invalid command parameters
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Service not found
- **409 Conflict**: Device busy or invalid state
- **500/502 Server Error**: Automatic retry with exponential backoff

All errors are logged with detailed information to help with troubleshooting.

## Command Response Handling

Commands are processed asynchronously by the Gardena API:

- **202 Accepted**: Command accepted for processing
- The device state will be updated on the next data refresh (every 30 seconds)
- No immediate confirmation of command execution is provided

## Best Practices

1. **Check Device State**: Before sending commands, check the current state of the device
2. **Use Appropriate Durations**: Don't set unnecessarily long durations for devices
3. **Handle Errors**: Always handle potential errors in your automations
4. **Monitor Logs**: Check the Home Assistant logs for any command-related issues
5. **Test Commands**: Test commands manually before using them in automations

## Troubleshooting

### Command Not Executed
- Check if the device is online (RF link state)
- Verify the device ID is correct
- Check the Home Assistant logs for error messages
- Ensure the device supports the requested command

### Device Not Responding
- Check the device's battery level
- Verify the RF link state is "ONLINE"
- Try sending a simple command first
- Check if the device is in maintenance mode

### Permission Errors
- Verify your API credentials are correct
- Check if your account has permission to control the device
- Ensure the device is not locked or in a restricted mode 