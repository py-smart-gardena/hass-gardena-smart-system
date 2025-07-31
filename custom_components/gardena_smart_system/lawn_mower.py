"""Support for Gardena Smart System lawn mowers."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lawn_mower import LawnMowerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_TYPE_MOWER
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System lawn mowers."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create lawn mower entities for each device
    entities = []
    
    for location_id, devices in coordinator.devices.items():
        for device_id, device_data in devices.items():
            # Add lawn mower entities if available
            if device_data.get("type") == SERVICE_TYPE_MOWER:
                entities.append(
                    GardenaLawnMower(coordinator, location_id, device_id, device_data)
                )

    async_add_entities(entities)


class GardenaLawnMower(LawnMowerEntity):
    """Representation of a Gardena lawn mower."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the lawn mower."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_lawn_mower"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} Lawn Mower"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success 