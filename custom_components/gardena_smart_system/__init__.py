"""The Gardena Smart System integration."""
import asyncio
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .gardena_client import GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gardena Smart System from a config entry."""
    _LOGGER.info("Setting up Gardena Smart System integration")

    # Get dev mode from environment
    dev_mode = os.getenv('GARDENA_DEV_MODE', 'false').lower() == 'true'
    
    # Create client
    client = GardenaSmartSystemClient(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        dev_mode=dev_mode,
    )

    # Create coordinator
    coordinator = GardenaSmartSystemCoordinator(hass, client)

    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        # Test the connection
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.shutdown()
        raise
    except Exception as err:
        _LOGGER.error("Failed to initialize Gardena Smart System: %s", err)
        await coordinator.shutdown()
        raise ConfigEntryNotReady(f"Failed to initialize: {err}") from err

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Gardena Smart System integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Shutdown coordinator
    if entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.shutdown()
        del hass.data[DOMAIN][entry.entry_id]

    return unload_ok 