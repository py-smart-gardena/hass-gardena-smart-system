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
from .entities import GardenaOnlineEntity, GardenaEntity

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
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            # Add online status sensors for all devices
            entities.append(GardenaOnlineBinarySensor(coordinator, device))

    async_add_entities(entities)


class GardenaOnlineBinarySensor(GardenaOnlineEntity, BinarySensorEntity):
    """Representation of a Gardena device online status sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the online status sensor."""
        super().__init__(coordinator, device)
        self._attr_name = f"{device.name} Online" 



