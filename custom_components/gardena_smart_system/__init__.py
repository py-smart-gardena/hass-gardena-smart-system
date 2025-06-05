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

    # Register services
    _LOGGER.debug("Registering Gardena Smart System services...")
    await _register_services(hass, gardena_system)

    _LOGGER.debug("Gardena Smart System component setup finished")
    return True


async def _register_services(hass: HomeAssistant, gardena_system):
    """Register integration services."""
    
    async def websocket_diagnostics_service(call):
        """Handle websocket diagnostics service call."""
        detailed = call.data.get("detailed", False)
        
        diagnostics = {
            "websocket_connected": gardena_system.is_websocket_connected,
            "websocket_task_status": gardena_system.websocket_task_status,
            "smart_system_status": gardena_system.smart_system.is_ws_connected if gardena_system.smart_system else False,
        }
        
        if detailed:
            diagnostics.update({
                "location_count": len(gardena_system.smart_system.locations) if gardena_system.smart_system else 0,
                "device_count": sum(len(loc.devices) for loc in gardena_system.smart_system.locations.values()) if gardena_system.smart_system else 0,
                "has_active_task": gardena_system._ws_task is not None and not gardena_system._ws_task.done(),
                "shutdown_event_set": gardena_system._shutdown_event.is_set(),
            })
        
        return diagnostics
    
    async def reload_service(call):
        """Handle reload service call."""
        _LOGGER.info("Reload service called")
        # Find the config entry for this integration
        for config_entry in hass.config_entries.async_entries(DOMAIN):
            _LOGGER.info(f"Reloading config entry: {config_entry.title}")
            await hass.config_entries.async_reload(config_entry.entry_id)
        
    hass.services.async_register(
        DOMAIN, 
        "websocket_diagnostics", 
        websocket_diagnostics_service,
        supports_response=True
    )
    
    hass.services.async_register(
        DOMAIN,
        "reload", 
        reload_service
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Gardena Smart System component")
    
    # Unload all platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Stop the GardenaSmartSystem and clean up resources
        gardena_system = hass.data[DOMAIN].get(GARDENA_SYSTEM)
        if gardena_system:
            _LOGGER.debug("Stopping Gardena Smart System")
            try:
                await gardena_system.stop()
                # Give a moment for the WebSocket to close properly
                _LOGGER.debug("Waiting for WebSocket connection to close...")
                await asyncio.sleep(2)
            except Exception as ex:
                _LOGGER.warning(f"Error during GardenaSmartSystem stop: {ex}")
        
        # Unregister services if this is the last config entry
        remaining_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN) 
            if e.entry_id != entry.entry_id
        ]
        if not remaining_entries:
            _LOGGER.debug("Unregistering Gardena Smart System services")
            hass.services.async_remove(DOMAIN, "websocket_diagnostics")
            hass.services.async_remove(DOMAIN, "reload")
        
        # Clean up stored data
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(GARDENA_SYSTEM, None)
            hass.data[DOMAIN].pop(GARDENA_LOCATION, None)
            # If no more entries, remove the domain entirely
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)
        
        _LOGGER.debug("Gardena Smart System component unloaded successfully")
    else:
        _LOGGER.error("Failed to unload Gardena Smart System platforms")
    
    return unload_ok


class GardenaSmartSystem:
    """A Gardena Smart System wrapper class."""

    def __init__(self, hass, client_id, client_secret):
        """Initialize the Gardena Smart System."""
        self._hass = hass
        self._ws_task = None
        self._shutdown_event = asyncio.Event()
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
            
            # Start WebSocket with proper task management
            self._ws_task = asyncio.create_task(
                self._managed_websocket_connection(location),
                name="gardena_websocket"
            )
            # Add task exception handling
            self._ws_task.add_done_callback(self._websocket_task_done_callback)
            _LOGGER.debug("Websocket task created and launched with management")
            
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

    async def _managed_websocket_connection(self, location):
        """Managed WebSocket connection with improved error handling and reconnection."""
        reconnect_delay = 5  # Initial delay in seconds
        max_reconnect_delay = 300  # Maximum delay (5 minutes)
        reconnect_attempts = 0
        
        while not self._shutdown_event.is_set():
            try:
                _LOGGER.debug(f"WebSocket connection attempt {reconnect_attempts + 1}")
                await self.smart_system.start_ws(location)
                # If we get here, the WebSocket loop ended normally
                if self._shutdown_event.is_set():
                    _LOGGER.debug("WebSocket connection ended due to shutdown")
                    break
                else:
                    _LOGGER.warning("WebSocket connection ended unexpectedly")
                    
            except Exception as ex:
                _LOGGER.error(f"WebSocket connection error: {type(ex).__name__}: {ex}")
                reconnect_attempts += 1
                
            # Exponential backoff for reconnection
            if not self._shutdown_event.is_set():
                current_delay = min(reconnect_delay * (2 ** min(reconnect_attempts - 1, 5)), max_reconnect_delay)
                _LOGGER.info(f"Reconnecting WebSocket in {current_delay} seconds (attempt {reconnect_attempts})")
                
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=current_delay)
                    break  # Shutdown was requested during wait
                except asyncio.TimeoutError:
                    continue  # Continue with reconnection attempt
                    
        _LOGGER.debug("WebSocket management task ending")

    def _websocket_task_done_callback(self, task):
        """Handle WebSocket task completion or failure."""
        if task.cancelled():
            _LOGGER.debug("WebSocket task was cancelled")
        elif task.exception():
            _LOGGER.error(f"WebSocket task failed with exception: {task.exception()}")
        else:
            _LOGGER.debug("WebSocket task completed normally")

    @property
    def is_websocket_connected(self):
        """Check if WebSocket is connected."""
        return (
            self._ws_task is not None 
            and not self._ws_task.done() 
            and self.smart_system.is_ws_connected
        )

    @property
    def websocket_task_status(self):
        """Get WebSocket task status for debugging."""
        if self._ws_task is None:
            return "not_started"
        elif self._ws_task.cancelled():
            return "cancelled"
        elif self._ws_task.done():
            if self._ws_task.exception():
                return f"failed: {self._ws_task.exception()}"
            else:
                return "completed"
        else:
            return "running"

    async def stop(self):
        _LOGGER.debug("Stopping GardenaSmartSystem")
        
        # Signal shutdown to WebSocket management
        self._shutdown_event.set()
        
        # Cancel WebSocket task if running
        if self._ws_task and not self._ws_task.done():
            _LOGGER.debug("Cancelling WebSocket task")
            self._ws_task.cancel()
            try:
                await asyncio.wait_for(self._ws_task, timeout=10.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                _LOGGER.debug("WebSocket task cancelled/timed out")
            except Exception as ex:
                _LOGGER.warning(f"Error while cancelling WebSocket task: {ex}")
        
        # Stop the underlying smart system
        await self.smart_system.quit()
        _LOGGER.debug("GardenaSmartSystem stopped")
