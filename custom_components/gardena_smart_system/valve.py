"""Support for Gardena valves (Water control, smart irrigation control)."""
import asyncio
import logging

from homeassistant.core import callback
from homeassistant.components.valve import ValveEntity, ValveEntityFeature, ValveDeviceClass
from homeassistant.const import ATTR_BATTERY_LEVEL

from .const import (
    ATTR_ACTIVITY,
    ATTR_BATTERY_STATE,
    ATTR_LAST_ERROR,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
    ATTR_SERIAL,
    CONF_SMART_IRRIGATION_DURATION,
    CONF_SMART_WATERING_DURATION,
    DEFAULT_SMART_IRRIGATION_DURATION,
    DEFAULT_SMART_WATERING_DURATION,
    DOMAIN,
    GARDENA_LOCATION,
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the valves platform."""

    entities = []
    for water_control in hass.data[DOMAIN][GARDENA_LOCATION].find_device_by_type("WATER_CONTROL"):
        entities.append(GardenaSmartWaterControl(water_control, config_entry.options))

    for smart_irrigation in hass.data[DOMAIN][GARDENA_LOCATION].find_device_by_type("SMART_IRRIGATION_CONTROL"):
        for valve in smart_irrigation.valves.values():
            entities.append(GardenaSmartIrrigationControl(
                smart_irrigation, valve['id'], config_entry.options))

    _LOGGER.debug(
        "Adding water control and smart irrigation control as valve: %s",
        entities)
    async_add_entities(entities, True)


class GardenaSmartWaterControl(ValveEntity):
    """Representation of a Gardena Smart Water Control."""

    def __init__(self, wc, options):
        """Initialize the Gardena Smart Water Control."""
        self._device = wc
        self._options = options
        self._name = f"{self._device.name}"
        self._unique_id = f"{self._device.serial}-valve"
        self._state = None
        self._error_message = ""

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a water valve."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    async def async_update(self):
        """Update the states of Gardena devices."""
        _LOGGER.debug("Running Gardena update")
        # Managing state
        state = self._device.valve_state
        _LOGGER.debug("Water control has state %s", state)
        if state in ["WARNING", "ERROR", "UNAVAILABLE"]:
            _LOGGER.debug("Water control has an error")
            self._state = False
            self._error_message = self._device.last_error_code
        else:
            _LOGGER.debug("Getting water control state")
            activity = self._device.valve_activity
            self._error_message = ""
            _LOGGER.debug("Water control has activity %s", activity)
            if activity == "CLOSED":
                self._state = False
            elif activity in ["MANUAL_WATERING", "SCHEDULED_WATERING"]:
                self._state = True
            else:
                _LOGGER.debug("Water control has none activity")

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def is_closed(self):
        """Return true if the valve is closed."""
        return not self._state

    @property
    def device_class(self):
        """Return the device class for water valves."""
        return ValveDeviceClass.WATER

    @property
    def supported_features(self):
        """Return the supported features."""
        return ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    @property
    def reports_position(self):
        """Return False as this valve does not report position."""
        return False

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.valve_state != "UNAVAILABLE"

    def error(self):
        """Return the error message."""
        return self._error_message

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the water valve."""
        return {
            ATTR_ACTIVITY: self._device.valve_activity,
            ATTR_BATTERY_LEVEL: self._device.battery_level,
            ATTR_BATTERY_STATE: self._device.battery_state,
            ATTR_RF_LINK_LEVEL: self._device.rf_link_level,
            ATTR_RF_LINK_STATE: self._device.rf_link_state,
            ATTR_LAST_ERROR: self._error_message,
        }

    @property
    def option_smart_watering_duration(self) -> int:
        return self._options.get(
            CONF_SMART_WATERING_DURATION, DEFAULT_SMART_WATERING_DURATION
        )

    async def async_open_valve(self):
        """Open the valve to start watering."""
        duration = self.option_smart_watering_duration * 60
        await self._device.start_seconds_to_override(duration)

    async def async_close_valve(self):
        """Close the valve to stop watering."""
        await self._device.stop_until_next_task()

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._device.serial)
            },
            "name": self._device.name,
            "manufacturer": "Gardena",
            "model": self._device.model_type,
        }


class GardenaSmartIrrigationControl(ValveEntity):
    """Representation of a Gardena Smart Irrigation Control."""

    def __init__(self, sic, valve_id, options):
        """Initialize the Gardena Smart Irrigation Control."""
        self._device = sic
        self._valve_id = valve_id
        self._options = options
        self._name = f"{self._device.name} - {self._device.valves[self._valve_id]['name']}"
        self._unique_id = f"{self._device.serial}-{self._valve_id}"
        self._state = None
        self._error_message = ""

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a smart irrigation control."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    async def async_update(self):
        """Update the states of Gardena devices."""
        _LOGGER.debug("Running Gardena update")
        # Managing state
        valve = self._device.valves[self._valve_id]
        _LOGGER.debug("Valve has state: %s", valve["state"])
        if valve["state"] in ["WARNING", "ERROR", "UNAVAILABLE"]:
            _LOGGER.debug("Valve has an error")
            self._state = False
            self._error_message = valve["last_error_code"]
        else:
            _LOGGER.debug("Getting Valve state")
            activity = valve["activity"]
            self._error_message = ""
            _LOGGER.debug("Valve has activity: %s", activity)
            if activity == "CLOSED":
                self._state = False
            elif activity in ["MANUAL_WATERING", "SCHEDULED_WATERING"]:
                self._state = True
            else:
                _LOGGER.debug("Valve has unknown activity")

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def is_closed(self):
        """Return true if the valve is closed."""
        return not self._state

    @property
    def device_class(self):
        """Return the device class for water valves."""
        return ValveDeviceClass.WATER

    @property
    def supported_features(self):
        """Return the supported features."""
        return ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    @property
    def reports_position(self):
        """Return False as this valve does not report position."""
        return False

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.valves[self._valve_id]["state"] != "UNAVAILABLE"

    def error(self):
        """Return the error message."""
        return self._error_message

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the smart irrigation control."""
        return {
            ATTR_ACTIVITY: self._device.valves[self._valve_id]["activity"],
            ATTR_RF_LINK_LEVEL: self._device.rf_link_level,
            ATTR_RF_LINK_STATE: self._device.rf_link_state,
            ATTR_LAST_ERROR: self._error_message,
        }

    @property
    def option_smart_irrigation_duration(self) -> int:
        return self._options.get(
            CONF_SMART_IRRIGATION_DURATION, DEFAULT_SMART_IRRIGATION_DURATION
        )

    async def async_open_valve(self):
        """Open the valve to start watering."""
        duration = self.option_smart_irrigation_duration * 60
        await self._device.start_seconds_to_override(duration, self._valve_id)

    async def async_close_valve(self):
        """Close the valve to stop watering."""
        await self._device.stop_until_next_task(self._valve_id)

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._device.serial)
            },
            "name": self._device.name,
            "manufacturer": "Gardena",
            "model": self._device.model_type,
        } 