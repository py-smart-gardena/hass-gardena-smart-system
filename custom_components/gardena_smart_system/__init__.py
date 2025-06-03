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

PLATFORMS = ["lawn_mower", "sensor", "switch", "valve", "binary_sensor", "button"]

# Create SSL context outside of event loop
_SSL_CONTEXT = get_ssl_context()

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Gardena Smart System integration."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Gardena Smart System component")
    
    # Log client_id for debugging (but not the secret)
    client_id = entry.data[CONF_CLIENT_ID]
    _LOGGER.debug(f"Using client_id: {client_id[:8]}...{client_id[-4:] if len(client_id) > 12 else '***'}")

    gardena_system = GardenaSmartSystem(
        hass,
        client_id=client_id,
        client_secret=entry.data[CONF_CLIENT_SECRET],
    )
    
    retry_count = 0
    max_retries = 5  # Limit retries to avoid infinite loop
    
    while retry_count < max_retries:
        try:
            _LOGGER.debug(f"Attempting to start Gardena Smart System (attempt {retry_count + 1}/{max_retries})")
            await gardena_system.start()
            _LOGGER.debug("Gardena Smart System started successfully")
            break  # If connection is successful, break out of loop
        except ConnectionError as ex:
            retry_count += 1
            _LOGGER.warning(f"Connection error (attempt {retry_count}/{max_retries}): {ex}")
            if retry_count < max_retries:
                _LOGGER.debug("Waiting 60 seconds before retry...")
                await asyncio.sleep(60)  # Wait for 60 seconds before trying to reconnect
            else:
                _LOGGER.error("Max retries reached for connection errors")
                return False
        except AccessDeniedError as ex:
            _LOGGER.error('Got Access Denied Error when setting up Gardena Smart System: %s', ex)
            _LOGGER.error('This usually means your client credentials are incorrect or your app doesn\'t have the required permissions')
            return False
        except InvalidClientError as ex:
            _LOGGER.error('Got Invalid Client Error when setting up Gardena Smart System: %s', ex)
            _LOGGER.error('This usually means your client_id is incorrect or the application is not properly configured')
            return False
        except MissingTokenError as ex:
            _LOGGER.error('Got Missing Token Error when setting up Gardena Smart System: %s', ex)
            _LOGGER.error('This usually means authentication failed or token refresh failed')
            return False
        except Exception as ex:
            _LOGGER.error(f'Unexpected error during Gardena Smart System setup (attempt {retry_count + 1}/{max_retries}): {type(ex).__name__}: {ex}')
            retry_count += 1
            if retry_count < max_retries:
                _LOGGER.debug("Waiting 60 seconds before retry...")
                await asyncio.sleep(60)
            else:
                _LOGGER.error("Max retries reached for unexpected errors")
                return False

    hass.data[DOMAIN][GARDENA_SYSTEM] = gardena_system

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda event: hass.async_create_task(gardena_system.stop()))

    _LOGGER.debug("Setting up platforms...")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Gardena Smart System component setup finished")
    return True


class GardenaSmartSystem:
    """A Gardena Smart System wrapper class."""

    def __init__(self, hass, client_id, client_secret):
        """Initialize the Gardena Smart System."""
        self._hass = hass
        _LOGGER.debug("Initializing GardenaSmartSystem wrapper")
        self.smart_system = SmartSystem(
            client_id=client_id,
            client_secret=client_secret,
            ssl_context=_SSL_CONTEXT  # Use the pre-created SSL context
        )

    async def start(self):
        try:
            _LOGGER.debug("Starting GardenaSmartSystem authentication process")
            await self.smart_system.authenticate()
            _LOGGER.debug("Authentication successful, updating locations...")
            
            await self.smart_system.update_locations()
            _LOGGER.debug(f"Found {len(self.smart_system.locations)} location(s)")

            if len(self.smart_system.locations) < 1:
                _LOGGER.error("No locations found in your Gardena account")
                _LOGGER.error("Please check if your Gardena account has any registered devices/locations")
                raise Exception("No locations found")

            # currently gardena supports only one location and gateway, so we can take the first
            location = list(self.smart_system.locations.values())[0]
            _LOGGER.debug(f"Using location: {location.name} ({location.id})")
            
            _LOGGER.debug("Updating devices for location...")
            await self.smart_system.update_devices(location)
            _LOGGER.debug(f"Found {len(location.devices)} device(s) in location")
            
            self._hass.data[DOMAIN][GARDENA_LOCATION] = location
            _LOGGER.debug("Starting GardenaSmartSystem websocket connection")
            asyncio.create_task(self.smart_system.start_ws(self._hass.data[DOMAIN][GARDENA_LOCATION]))
            _LOGGER.debug("Websocket task created and launched")
            
        except AuthenticationException as ex:
            _LOGGER.error(f"Authentication failed: {ex.message}")
            _LOGGER.error("Please check your client_id and client_secret, or create a new app in the Gardena API portal")
            raise
        except Exception as ex:
            _LOGGER.error(f"Error during GardenaSmartSystem start: {type(ex).__name__}: {ex}")
            _LOGGER.error("If this is a 404 error, it might indicate:")
            _LOGGER.error("1. Your API credentials don't have access to the locations endpoint")
            _LOGGER.error("2. Your Gardena account has no registered locations/devices")
            _LOGGER.error("3. There might be an issue with the Gardena API service")
            raise

    async def stop(self):
        _LOGGER.debug("Stopping GardenaSmartSystem")
        await self.smart_system.quit()
        _LOGGER.debug("GardenaSmartSystem stopped")
