"""Support for Gardena Smart System devices."""
import asyncio
import logging

from gardena.exceptions.authentication_exception import AuthenticationException
from gardena.smart_system import SmartSystem, get_ssl_context
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from oauthlib.oauth2.rfc6749.errors import (
    AccessDeniedError,
    InvalidClientError,
    MissingTokenError,
)

from .const import (
    DOMAIN,
    GARDENA_LOCATION,
    GARDENA_SYSTEM,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["lawn_mower", "sensor", "switch", "binary_sensor", "button"]

# Create SSL context outside of event loop
_SSL_CONTEXT = get_ssl_context()

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Gardena Smart System integration."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Gardena Smart System component")

    gardena_system = GardenaSmartSystem(
        hass,
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
    )
    while True:
        try:
            await gardena_system.start()
            break  # If connection is successful, return True
        except ConnectionError:
            await asyncio.sleep(60)  # Wait for 60 seconds before trying to reconnect
        except AccessDeniedError as ex:
            _LOGGER.error('Got Access Denied Error when setting up Gardena Smart System: %s', ex)
            return False
        except InvalidClientError as ex:
            _LOGGER.error('Got Invalid Client Error when setting up Gardena Smart System: %s', ex)
            return False
        except MissingTokenError as ex:
            _LOGGER.error('Got Missing Token Error when setting up Gardena Smart System: %s', ex)
            return False

    hass.data[DOMAIN][GARDENA_SYSTEM] = gardena_system

    # /Markus:  origonal: hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda event: hass.async_create_task(gardena_system.stop()))
    # The EVENT_HOMEASSISTANT_STOP listener can be called from a non-event-loop thread.
    # To prevent a RuntimeError, we must use call_soon_threadsafe to safely
    # schedule the shutdown task on the main event loop.
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        lambda event: hass.loop.call_soon_threadsafe(
            hass.async_create_task, gardena_system.stop()
        ),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Gardena Smart System component setup finished")
    return True


class GardenaSmartSystem:
    """A Gardena Smart System wrapper class."""

    def __init__(self, hass, client_id, client_secret):
        """Initialize the Gardena Smart System."""
        self._hass = hass
        self.smart_system = SmartSystem(
            client_id=client_id,
            client_secret=client_secret,
            ssl_context=_SSL_CONTEXT  # Use the pre-created SSL context
        )

    async def start(self):
        try:
            _LOGGER.debug("Starting GardenaSmartSystem")
            await self.smart_system.authenticate()
            await self.smart_system.update_locations()

            if len(self.smart_system.locations) < 1:
                _LOGGER.error("No locations found")
                raise Exception("No locations found")

            # currently gardena supports only one location and gateway, so we can take the first
            location = list(self.smart_system.locations.values())[0]
            _LOGGER.debug(f"Using location: {location.name} ({location.id})")
            await self.smart_system.update_devices(location)
            self._hass.data[DOMAIN][GARDENA_LOCATION] = location
            _LOGGER.debug("Starting GardenaSmartSystem websocket")
            asyncio.create_task(self.smart_system.start_ws(self._hass.data[DOMAIN][GARDENA_LOCATION]))
            _LOGGER.debug("Websocket thread launched !")
        except AuthenticationException as ex:
            _LOGGER.error(
                f"Authentication failed : {ex.message}. You may need to check your token or create a new app in the gardena api and use the new token.")

    async def stop(self):
        _LOGGER.debug("Stopping GardenaSmartSystem")
        await self.smart_system.quit()
