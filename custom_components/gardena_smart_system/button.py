"""Support for Gardena Smart System buttons."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_platform

from .const import (
    DOMAIN,
    GARDENA_LOCATION,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Gardena Smart System buttons."""
    entities = []
    for mower in hass.data[DOMAIN][GARDENA_LOCATION].find_device_by_type("MOWER"):
        entities.append(GardenaStartOverrideButton(mower, config_entry.options))
        entities.append(GardenaReturnToDockButton(mower))

    _LOGGER.debug("Adding mower buttons: %s", entities)
    async_add_entities(entities, True)


class GardenaStartOverrideButton(ButtonEntity):
    """Representation of a Gardena Start Override button."""

    def __init__(self, mower, options):
        """Initialize the Gardena Start Override button."""
        self._device = mower
        self._options = options
        self._name = f"{self._device.name} Start Override"
        self._unique_id = f"{self._device.serial}-start-override"

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a button."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.state != "UNAVAILABLE"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {
                (DOMAIN, self._device.serial)
            },
            "name": self._device.name,
            "manufacturer": "Gardena",
            "model": self._device.model_type,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        duration = self._options.get("mower_duration", 60) * 60  # Convert minutes to seconds
        await self._device.start_seconds_to_override(duration)


class GardenaReturnToDockButton(ButtonEntity):
    """Representation of a Gardena Return to Dock button."""

    def __init__(self, mower):
        """Initialize the Gardena Return to Dock button."""
        self._device = mower
        self._name = f"{self._device.name} Return to Dock"
        self._unique_id = f"{self._device.serial}-return-to-dock"

    async def async_added_to_hass(self):
        """Subscribe to events."""
        self._device.add_callback(self.update_callback)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a button."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def available(self):
        """Return True if the device is available."""
        return self._device.state != "UNAVAILABLE"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {
                (DOMAIN, self._device.serial)
            },
            "name": self._device.name,
            "manufacturer": "Gardena",
            "model": self._device.model_type,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.park_until_next_task() 