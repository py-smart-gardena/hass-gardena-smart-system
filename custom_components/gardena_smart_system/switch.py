"""Support for Gardena Smart System switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_TYPE_POWER_SOCKET
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System switches."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create switch entities for each device
    entities = []
    
    for location_id, devices in coordinator.devices.items():
        for device_id, device_data in devices.items():
            # Add power socket switches if available
            if device_data.get("type") == SERVICE_TYPE_POWER_SOCKET:
                entities.append(
                    GardenaPowerSocketSwitch(coordinator, location_id, device_id, device_data)
                )

    async_add_entities(entities)


class GardenaPowerSocketSwitch(SwitchEntity):
    """Representation of a Gardena power socket switch."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_switch"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} Switch"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # This is a placeholder - implement based on device state
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # This is a placeholder - implement device control
        _LOGGER.info("Turning on %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # This is a placeholder - implement device control
        _LOGGER.info("Turning off %s", self._attr_name)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success 