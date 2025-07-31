"""Constants for the Gardena Smart System integration."""
from __future__ import annotations

from typing import Final

# Domain
DOMAIN: Final = "gardena_smart_system"

# Configuration keys
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"

# API constants
API_BASE_URL: Final = "https://api.smart.gardena.dev/v2"
API_TIMEOUT: Final = 30

# Device types
DEVICE_TYPE_MOWER: Final = "MOWER"
DEVICE_TYPE_VALVE: Final = "VALVE"
DEVICE_TYPE_POWER_SOCKET: Final = "POWER_SOCKET"
DEVICE_TYPE_SENSOR: Final = "SENSOR"

# Service types
SERVICE_TYPE_COMMON: Final = "COMMON"
SERVICE_TYPE_MOWER: Final = "MOWER"
SERVICE_TYPE_VALVE: Final = "VALVE"
SERVICE_TYPE_POWER_SOCKET: Final = "POWER_SOCKET"
SERVICE_TYPE_SENSOR: Final = "SENSOR"

# Mower states
MOWER_STATE_OK: Final = "OK"
MOWER_STATE_WARNING: Final = "WARNING"
MOWER_STATE_ERROR: Final = "ERROR"
MOWER_STATE_UNAVAILABLE: Final = "UNAVAILABLE"

# Mower activities
MOWER_ACTIVITY_PAUSED: Final = "PAUSED"
MOWER_ACTIVITY_CUTTING: Final = "OK_CUTTING"
MOWER_ACTIVITY_SEARCHING: Final = "OK_SEARCHING"
MOWER_ACTIVITY_LEAVING: Final = "OK_LEAVING"
MOWER_ACTIVITY_CHARGING: Final = "OK_CHARGING"
MOWER_ACTIVITY_PARKED: Final = "PARKED_TIMER"

# Update intervals
UPDATE_INTERVAL: Final = 60  # seconds 