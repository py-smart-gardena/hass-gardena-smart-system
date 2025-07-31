"""Support for Gardena Smart System binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System binary sensors."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create binary sensor entities for each device
    entities = []
    
    for location_id, devices in coordinator.devices.items():
        for device_id, device_data in devices.items():
            # Add online status sensors for all devices
            entities.append(
                GardenaOnlineSensor(coordinator, location_id, device_id, device_data)
            )

    async_add_entities(entities)


class GardenaOnlineSensor(BinarySensorEntity):
    """Representation of a Gardena device online status sensor."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_online"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} Online"

    @property
    def is_on(self) -> bool:
        """Return true if the device is online."""
        # This is a placeholder - implement based on device state
        return True

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success 