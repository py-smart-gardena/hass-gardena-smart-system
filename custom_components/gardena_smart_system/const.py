"""Constants for the Gardena Smart System integration."""
from __future__ import annotations

from typing import Final

from homeassistant.components.lawn_mower import LawnMowerActivity

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

# Gardena service states that represent an actual error condition. The lawn
# mower entity only reports LawnMowerActivity.ERROR when the service state is
# one of these — otherwise an unmapped/NONE activity (e.g. the mower stopped in
# the garden out of battery) falls back to PAUSED instead of contradicting the
# mower_error sensor, which reports "no error". See #375.
MOWER_ERROR_STATES: Final = frozenset({MOWER_STATE_ERROR, MOWER_STATE_WARNING})

# Mower activities
MOWER_ACTIVITY_PAUSED: Final = "PAUSED"
MOWER_ACTIVITY_PAUSED_IN_CS: Final = "PAUSED_IN_CS"
MOWER_ACTIVITY_CUTTING: Final = "OK_CUTTING"
MOWER_ACTIVITY_CUTTING_TIMER_OVERRIDDEN: Final = "OK_CUTTING_TIMER_OVERRIDDEN"
MOWER_ACTIVITY_SEARCHING: Final = "OK_SEARCHING"
MOWER_ACTIVITY_LEAVING: Final = "OK_LEAVING"
MOWER_ACTIVITY_CHARGING: Final = "OK_CHARGING"
MOWER_ACTIVITY_PARKED: Final = "PARKED_TIMER"
MOWER_ACTIVITY_PARKED_TIMER: Final = "PARKED_TIMER"
MOWER_ACTIVITY_PARKED_PARK_SELECTED: Final = "PARKED_PARK_SELECTED"
MOWER_ACTIVITY_PARKED_AUTOTIMER: Final = "PARKED_AUTOTIMER"
MOWER_ACTIVITY_PARKED_FROST: Final = "PARKED_FROST"
MOWER_ACTIVITY_PARKED_NO_LIGHT: Final = "PARKED_NO_LIGHT"
MOWER_ACTIVITY_PARKED_MOWING_COMPLETED: Final = "PARKED_MOWING_COMPLETED"
MOWER_ACTIVITY_PARKED_RAIN: Final = "PARKED_RAIN"
MOWER_ACTIVITY_PARKED_DAILY_LIMIT_REACHED: Final = "PARKED_DAILY_LIMIT_REACHED"
MOWER_ACTIVITY_STOPPED_IN_GARDEN: Final = "STOPPED_IN_GARDEN"
MOWER_ACTIVITY_INITIATE_NEXT_ACTION: Final = "INITIATE_NEXT_ACTION"
MOWER_ACTIVITY_SEARCHING_FOR_SATELLITES: Final = "SEARCHING_FOR_SATELLITES"
MOWER_ACTIVITY_NONE: Final = "NONE"

# Mower activity mapping to Home Assistant
MOWER_ACTIVITY_MAP: Final = {
    MOWER_ACTIVITY_PAUSED: LawnMowerActivity.PAUSED,
    MOWER_ACTIVITY_PAUSED_IN_CS: LawnMowerActivity.PAUSED,
    MOWER_ACTIVITY_CUTTING: LawnMowerActivity.MOWING,
    MOWER_ACTIVITY_CUTTING_TIMER_OVERRIDDEN: LawnMowerActivity.MOWING,
    MOWER_ACTIVITY_SEARCHING: LawnMowerActivity.RETURNING,
    MOWER_ACTIVITY_LEAVING: LawnMowerActivity.MOWING,
    MOWER_ACTIVITY_CHARGING: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_TIMER: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_PARK_SELECTED: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_AUTOTIMER: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_FROST: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_NO_LIGHT: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_MOWING_COMPLETED: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_RAIN: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_PARKED_DAILY_LIMIT_REACHED: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_STOPPED_IN_GARDEN: LawnMowerActivity.DOCKED,
    MOWER_ACTIVITY_INITIATE_NEXT_ACTION: LawnMowerActivity.MOWING,
    MOWER_ACTIVITY_SEARCHING_FOR_SATELLITES: LawnMowerActivity.DOCKED,
    # NONE is intentionally not mapped: the entity decides between ERROR and
    # PAUSED based on the Gardena service state instead of assuming an error.
    # See GardenaLawnMower.activity and MOWER_ERROR_STATES (#375).
}

# Mower informational codes — operational states that are NOT errors.
# The mower_error sensor returns "no_message" when last_error_code is in this set
# so that user automations trigger only on real actionable errors.
MOWER_INFORMATIONAL_CODES: Final = frozenset({
    "no_message",                   # Already "no error"
    "uninitialised",                # Normal boot state
    "parked_daily_limit_reached",   # Daily schedule limit reached — normal operation
    "outside_working_area",         # Mower returned to base outside its zone — normal
    "off_disabled",                 # Disabled manually by user
    "off_hatch_open",               # Hatch open for maintenance
    "off_hatch_closed",             # Hatch closed — normal state
    "wait_updating",                # Firmware update in progress
    "wait_power_up",                # Booting up
    "wait_stop_pressed",            # Stop button held — user-initiated maintenance
    "wait_for_safety_pin",          # Waiting for safety pin — user-initiated maintenance
    "guide_calibration_accomplished",  # Calibration completed successfully
    "connection_changed",           # Network state change — informational
    "connection_not_changed",       # Network state change — informational
})

# WebSocket configuration
WEBSOCKET_RECONNECT_DELAY: Final = 5  # seconds
WEBSOCKET_MAX_RECONNECT_ATTEMPTS: Final = 10

# Valve duration configuration
CONF_VALVE_DURATIONS: Final = "valve_durations"
DEFAULT_VALVE_DURATION_SECONDS: Final = 3600

# Attribute names
ATTR_BATTERY_STATE: Final = "battery_state"
ATTR_RF_LINK_LEVEL: Final = "rf_link_level"
ATTR_RF_LINK_STATE: Final = "rf_link_state" 