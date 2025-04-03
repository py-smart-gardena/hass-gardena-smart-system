"""Support for Gardena mower."""
import asyncio
import logging
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
)
from homeassistant.components.lawn_mower import (
    LawnMowerEntity,
    LawnMowerEntityFeature,
    LawnMowerActivity
)
from homeassistant.helpers import config_validation as cv, entity_platform
from .const import (
    ATTR_ACTIVITY,
    ATTR_BATTERY_STATE,
    ATTR_NAME,
    ATTR_OPERATING_HOURS,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
    ATTR_SERIAL,
    ATTR_LAST_ERROR,
    ATTR_ERROR,
    ATTR_STATE,
    ATTR_STINT_START,
    ATTR_STINT_END,
    CONF_MOWER_DURATION,
    DEFAULT_MOWER_DURATION,
    DOMAIN,
    GARDENA_LOCATION,
)


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

SUPPORT_GARDENA = (
    LawnMowerEntityFeature.START_MOWING |
    LawnMowerEntityFeature.PAUSE |
    LawnMowerEntityFeature.DOCK
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Gardena smart mower system."""
    entities = []
    for mower in hass.data[DOMAIN][GARDENA_LOCATION].find_device_by_type("MOWER"):
        entities.append(GardenaSmartMowerLawnMowerEntity(hass, mower, config_entry.options))

    _LOGGER.debug("Adding mower as lawn_mower: %s", entities)
    async_add_entities(entities, True)
    
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "start_override",
        {
            vol.Required("duration"): cv.positive_int 
        },
        "async_start_override",
    )


class GardenaSmartMowerLawnMowerEntity(LawnMowerEntity):
    """Representation of a Gardena Connected Mower."""

    def __init__(self, hass, mower, options):
        """Initialize the Gardena Connected Mower."""
        self.hass = hass
        self._device = mower
        self._options = options
        self._name = "{}".format(self._device.name)
        self._unique_id = f"{self._device.serial}-mower"
        self._activity = None
        self._error_message = ""
        self._stint_start = None
        self._stint_end = None

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a lawn_mower."""
        return False

    @property
    def activity(self) -> LawnMowerActivity:
        """Return the state of the mower."""
        return self._activity

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    async def async_update(self):
        """Update the states of Gardena devices."""
        _LOGGER.debug("Running Gardena update")
        # Managing state
        state = self._device.state
        _LOGGER.debug("Mower has state %s", state)
        if state in ["WARNING", "ERROR", "UNAVAILABLE"]:
            self._error_message = self._device.last_error_code
            if self._device.last_error_code == "PARKED_DAILY_LIMIT_REACHED":
                self._activity = None
            else:
                _LOGGER.debug("Mower has an error")
                self._activity = LawnMowerActivity.ERROR
        else:
            _LOGGER.debug("Getting mower state")
            activity = self._device.activity
            _LOGGER.debug("Mower has activity %s", activity)
            if activity == "PAUSED":
                self._activity = LawnMowerActivity.PAUSED
            elif activity in [
                "OK_CUTTING",
                "OK_CUTTING_TIMER_OVERRIDDEN",
                "OK_LEAVING",
            ]:
                if self._activity != LawnMowerActivity.MOWING:
                    self._stint_start = datetime.now()
                    self._stint_end = None
                self._activity = LawnMowerActivity.MOWING
            elif activity == "OK_SEARCHING":
                if self._activity == LawnMowerActivity.MOWING:
                    self._stint_end = datetime.now()
                self._activity =  LawnMowerActivity.RETURNING
            elif activity in [
                "OK_CHARGING",
                "PARKED_TIMER",
                "PARKED_PARK_SELECTED",
                "PARKED_AUTOTIMER",
            ]:
                self._activity = LawnMowerActivity.DOCKED
            elif activity == "NONE":
                self._activity = None
                _LOGGER.debug("Mower has no activity")

    @property
    def name(self):
        """Return the name of the device."""
        return self._device.name

    @property
    def supported_features(self):
        """Flag lawn mower robot features that are supported."""
        return SUPPORT_GARDENA

    @property
    def battery_level(self):
        """Return the battery level of the lawn mower."""
        return self._device.battery_level

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.state != "UNAVAILABLE"

    def error(self):
        """Return the error message."""
        if self._activity == LawnMowerActivity.ERROR:
            return self._error_message
        return ""

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the lawn mower."""
        return {
            ATTR_ACTIVITY: self._device.activity,
            ATTR_BATTERY_LEVEL: self._device.battery_level,
            ATTR_BATTERY_STATE: self._device.battery_state,
            ATTR_RF_LINK_LEVEL: self._device.rf_link_level,
            ATTR_RF_LINK_STATE: self._device.rf_link_state,
            ATTR_OPERATING_HOURS: self._device.operating_hours,
            ATTR_LAST_ERROR: self._device.last_error_code,
            ATTR_ERROR: "NONE" if self._device.activity != "NONE" else self._device.last_error_code,
            ATTR_STATE: self._device.activity if self._device.activity != "NONE" else self._device.last_error_code,
            ATTR_STINT_START: self._stint_start,
            ATTR_STINT_END: self._stint_end
        }

    @property
    def option_mower_duration(self) -> int:
        return self._options.get(CONF_MOWER_DURATION, DEFAULT_MOWER_DURATION)

    async def async_start_mowing(self) -> None:
        """Resume schedule."""
        await self._device.start_dont_override()

    async def async_dock(self) -> None:
        """Parks the mower until next schedule."""
        await self._device.park_until_next_task()

    async def async_pause(self) -> None:
        """Parks the mower until further notice."""
        await self._device.park_until_further_notice()
        
    async def async_start_override(
        self, duration: int
    ) -> None:
        """Start the mower using Gardena API command START_SECONDS_TO_OVERRIDE."""
        await self._device.start_seconds_to_override(duration)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

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
