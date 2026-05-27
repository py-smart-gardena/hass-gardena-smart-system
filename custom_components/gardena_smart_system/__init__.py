"""Support for Gardena Smart System devices."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_CONFIG_ENTRY_ID, DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .credential_validation import (
    SERVICE_ERROR_MESSAGES,
    async_validate_gardena_credentials,
)
from .services import GardenaServiceManager

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_UPDATE_CREDENTIALS = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)

SERVICE_SCHEMA_START_RECONFIGURE = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): str,
    }
)

PLATFORMS = [
    Platform.LAWN_MOWER,
    Platform.NUMBER,
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

    def _get_config_entry(config_entry_id: str | None) -> ConfigEntry:
        """Resolve the Gardena config entry."""
        if config_entry_id:
            entry = hass.config_entries.async_get_entry(config_entry_id)
            if entry is None or entry.domain != DOMAIN:
                raise ServiceValidationError(
                    f"Unknown Gardena config entry: {config_entry_id}"
                )
            return entry

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("Gardena Smart System is not configured")
        if len(entries) > 1:
            raise ServiceValidationError(
                "config_entry_id is required when multiple Gardena entries exist"
            )
        return entries[0]

    async def _async_reload_service(call: ServiceCall) -> None:
        """Reload all config entries for this integration."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    async def _async_update_credentials_service(call: ServiceCall) -> None:
        """Validate and store API credentials (works while integration is disabled)."""
        entry = _get_config_entry(call.data.get(CONF_CONFIG_ENTRY_ID))
        user_input = {
            CONF_CLIENT_ID: call.data[CONF_CLIENT_ID],
            CONF_CLIENT_SECRET: call.data[CONF_CLIENT_SECRET],
        }
        errors = await async_validate_gardena_credentials(user_input)
        if errors:
            error_key = errors.get("base", "unknown")
            message = SERVICE_ERROR_MESSAGES.get(error_key, error_key)
            raise ServiceValidationError(message)

        hass.config_entries.async_update_entry(entry, data=user_input)
        if entry.disabled_by is None:
            await hass.config_entries.async_reload(entry.entry_id)
            _LOGGER.info("Gardena credentials updated and integration reloaded")
        else:
            _LOGGER.info(
                "Gardena credentials updated for disabled entry %s; "
                "enable the integration to connect",
                entry.entry_id,
            )

    async def _async_start_reconfigure_service(call: ServiceCall) -> None:
        """Open the credential dialog (works while integration is disabled)."""
        entry = _get_config_entry(call.data.get(CONF_CONFIG_ENTRY_ID))
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )

    hass.services.async_register(DOMAIN, "reload", _async_reload_service)
    hass.services.async_register(
        DOMAIN,
        "update_credentials",
        _async_update_credentials_service,
        schema=SERVICE_SCHEMA_UPDATE_CREDENTIALS,
    )
    hass.services.async_register(
        DOMAIN,
        "start_reconfigure",
        _async_start_reconfigure_service,
        schema=SERVICE_SCHEMA_START_RECONFIGURE,
    )

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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """Allow removal of devices no longer reported by the Gardena API."""
    coordinator = hass.data[DOMAIN].get(config_entry.entry_id)
    if not coordinator:
        return True

    known_device_ids: set[str] = set()
    for location in coordinator.locations.values():
        for device_id in location.devices:
            known_device_ids.add(device_id)

    return not device_entry.identifiers.intersection(
        (DOMAIN, device_id) for device_id in known_device_ids
    )
