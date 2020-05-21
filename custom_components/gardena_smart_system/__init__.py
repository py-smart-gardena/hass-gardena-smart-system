"""Support for Gardena Smart System devices."""
import logging

from gardena.smart_system import SmartSystem
from oauthlib.oauth2.rfc6749.errors import (
    AccessDeniedError,
    InvalidClientError,
    MissingTokenError,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from .const import(
    ATTR_ACTIVITY,
    ATTR_BATTERY_STATE,
    ATTR_LAST_ERRORS,
    ATTR_NAME,
    ATTR_OPERATING_HOURS,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
    ATTR_SERIAL,
    CONF_APPLICATION_KEY,
    DOMAIN,
    GARDENA_CONFIG,
    GARDENA_LOCATION,
    GARDENA_SYSTEM,
)


_LOGGER = logging.getLogger(__name__)

PLATFORMS = ("vacuum", "sensor", "switch")

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Gardena Smart System integration."""
    _LOGGER.debug("Initialising Gardena Smart System")

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[GARDENA_CONFIG] = entry.data
    gardena_system = GardenaSmartSystem(hass, entry.data)

    try:
        await hass.async_add_executor_job(gardena_system.start)
        _LOGGER.debug("Gardena Smart System component initialised")
    except (AccessDeniedError, InvalidClientError, MissingTokenError) as exception:
        _LOGGER.error("Gardena Smart System component could not be initialised")
        print(exception)
        return False


    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


class GardenaSmartSystem:
    """A Gardena Smart System wrapper class."""

    def __init__(self, hass, config, smart_system=SmartSystem):
        """Initialize the Gardena Smart System."""
        self.config = config
        self._hass = hass
        self.smart_system = smart_system(
            email=self.config[CONF_EMAIL],
            password=self.config[CONF_PASSWORD],
            client_id=self.config[CONF_APPLICATION_KEY],
        )


    def start(self):
        _LOGGER.debug("Starting GardenaSmartSystem")
        self.smart_system.authenticate()
        self.smart_system.update_locations()

        if len(self.smart_system.locations) < 1:
            _LOGGER.error("No locations found")
            raise Exception("No locations found")

        # currently gardena supports only one location and gateway, so we can take the first
        location = list(self.smart_system.locations.values())[0]
        _LOGGER.debug(f"Using location: {location.name} ({location.id})")
        self.smart_system.update_devices(location)
        self._hass.data[GARDENA_LOCATION] = location
        _LOGGER.debug("Starting GardenaSmartSystem websocket")
        self.smart_system.start_ws(self._hass.data[GARDENA_LOCATION])


    def stop(self):
        _LOGGER.debug("Stopping GardenaSmartSystem")
        self.smart_system.quit()
