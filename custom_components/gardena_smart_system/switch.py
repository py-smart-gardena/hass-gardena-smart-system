"""Support for Gardena switch (Power control)."""
import asyncio
import logging

from homeassistant.core import callback
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_BATTERY_LEVEL

from .const import (
    ATTR_ACTIVITY,
    ATTR_BATTERY_STATE,
    ATTR_LAST_ERROR,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
    ATTR_SERIAL,
    DOMAIN,
    GARDENA_LOCATION,
)
from .sensor import GardenaSensor


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the switches platform."""

    entities = []
    # Note: Water control and smart irrigation control are now handled by the valve platform
    for power_switch in hass.data[DOMAIN][GARDENA_LOCATION].find_device_by_type("POWER_SOCKET"):
        entities.append(GardenaPowerSocket(power_switch))

    _LOGGER.debug(
        "Adding power socket as switch: %s",
        entities)
    async_add_entities(entities, True)


class GardenaPowerSocket(SwitchEntity):
    """Representation of a Gardena Power Socket."""

    def __init__(self, ps):
        """Initialize the Gardena Power Socket."""
        self._device = ps
        self._name = f"{self._device.name}"
        self._unique_id = f"{self._device.serial}"
        self._state = None
        self._error_message = ""

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a power socket."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    async def async_update(self):
        """Update the states of Gardena devices."""
        _LOGGER.debug("Running Gardena update")
        # Managing state
        state = self._device.state
        _LOGGER.debug("Power socket has state %s", state)
        if state in ["WARNING", "ERROR", "UNAVAILABLE"]:
            _LOGGER.debug("Power socket has an error")
            self._state = False
            self._error_message = self._device.last_error_code
        else:
            _LOGGER.debug("Getting Power socket state")
            activity = self._device.activity
            self._error_message = ""
            _LOGGER.debug("Power socket has activity %s", activity)
            if activity == "OFF":
                self._state = False
            elif activity in ["FOREVER_ON", "TIME_LIMITED_ON", "SCHEDULED_ON"]:
                self._state = True
            else:
                _LOGGER.debug("Power socket has none activity")

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def is_on(self):
        """Return true if it is on."""
        return self._state

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.state != "UNAVAILABLE"

    def error(self):
        """Return the error message."""
        return self._error_message

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the power switch."""
        return {
            ATTR_ACTIVITY: self._device.activity,
            ATTR_RF_LINK_LEVEL: self._device.rf_link_level,
            ATTR_RF_LINK_STATE: self._device.rf_link_state,
            ATTR_LAST_ERROR: self._error_message,
        }

    def turn_on(self, **kwargs):
        """Start watering."""
        return asyncio.run_coroutine_threadsafe(
            self._device.start_override(), self.hass.loop
        ).result()

    def turn_off(self, **kwargs):
        """Stop watering."""
        return asyncio.run_coroutine_threadsafe(
            self._device.stop_until_next_task(), self.hass.loop
        ).result()

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
