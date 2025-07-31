"""Support for Gardena Smart System valves."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import ValveEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_TYPE_VALVE
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System valves."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create valve entities for each device
    entities = []
    
    for location_id, devices in coordinator.devices.items():
        for device_id, device_data in devices.items():
            # Add valve entities if available
            if device_data.get("type") == SERVICE_TYPE_VALVE:
                entities.append(
                    GardenaValve(coordinator, location_id, device_id, device_data)
                )

    async_add_entities(entities)


class GardenaValve(ValveEntity):
    """Representation of a Gardena valve."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the valve."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_valve"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} Valve"

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        # This is a placeholder - implement based on device state
        return True

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        # This is a placeholder - implement device control
        _LOGGER.info("Opening valve %s", self._attr_name)

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        # This is a placeholder - implement device control
        _LOGGER.info("Closing valve %s", self._attr_name)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success 