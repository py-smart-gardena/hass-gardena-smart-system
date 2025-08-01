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
            # Add battery sensors if available
            if "COMMON" in device.services:
                common_services = device.services["COMMON"]
                _LOGGER.info(f"Found {len(common_services)} common services for device: {device.name} ({device.id})")
                for common_service in common_services:
                    _LOGGER.info(f"Creating battery sensor for service: {common_service.id}")
                    entities.append(GardenaBatterySensor(coordinator, device, common_service))
            else:
                _LOGGER.debug(f"Device {device.name} ({device.id}) has no COMMON service")

    async_add_entities(entities)


class GardenaOnlineBinarySensor(GardenaOnlineEntity, BinarySensorEntity):
    """Representation of a Gardena device online status sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the online status sensor."""
        super().__init__(coordinator, device)
        self._attr_name = f"{device.name} Online" 


class GardenaBatterySensor(GardenaEntity, BinarySensorEntity):
    """Representation of a Gardena battery sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, common_service) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, device, "COMMON")
        self._attr_unique_id = f"{device.id}_{common_service.id}_battery"
        self._attr_name = f"{device.name} Battery"
        self._common_service = common_service

    @property
    def is_on(self) -> bool:
        """Return true if battery is in a normal state."""
        if self._common_service and self._common_service.battery_state:
            # States considered normal: OK, CHARGING, NO_BATTERY
            # States considered problematic: LOW, REPLACE_NOW, OUT_OF_OPERATION, UNKNOWN
            return self._common_service.battery_state in ["OK", "CHARGING", "NO_BATTERY"]
        return False
