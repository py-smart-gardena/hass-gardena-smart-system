"""Support for Gardena Smart System devices."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .services import GardenaServiceManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Gardena Smart System integration."""
    _LOGGER.info("Setting up Gardena Smart System integration")
    
    # Initialize service manager once per Home Assistant instance
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        service_manager = GardenaServiceManager(hass)
        hass.data[DOMAIN]["service_manager"] = service_manager
        _LOGGER.info("Gardena Smart System services initialized")
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gardena Smart System from a config entry."""
    _LOGGER.info("Setting up Gardena Smart System component")
    
    # Create client
    from .gardena_client import GardenaSmartSystemClient
    
    client = GardenaSmartSystemClient(
        client_id=entry.data["client_id"],
        client_secret=entry.data["client_secret"],
        dev_mode=True,  # Enable dev mode to bypass SSL issues on macOS
    )
    
    # Create coordinator
    coordinator = GardenaSmartSystemCoordinator(
        hass,
        client=client,
    )
    
    # Store coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Start the coordinator
    await coordinator.async_config_entry_first_refresh()
    
    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Gardena Smart System component setup finished")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Gardena Smart System component")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove coordinator from hass data
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    
    return unload_ok
