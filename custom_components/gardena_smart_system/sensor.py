"""Support for Gardena Smart System sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
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
    """Set up Gardena Smart System sensors."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create sensor entities for each device
    entities = []
    
    for location_id, devices in coordinator.devices.items():
        for device_id, device_data in devices.items():
            # Add battery level sensor if available
            if "batteryLevel" in device_data.get("attributes", {}):
                entities.append(
                    GardenaBatterySensor(coordinator, location_id, device_id, device_data)
                )
            
            # Add temperature sensors if available
            if "soilTemperature" in device_data.get("attributes", {}):
                entities.append(
                    GardenaTemperatureSensor(coordinator, location_id, device_id, device_data, "soilTemperature", "Soil Temperature")
                )
            
            if "ambientTemperature" in device_data.get("attributes", {}):
                entities.append(
                    GardenaTemperatureSensor(coordinator, location_id, device_id, device_data, "ambientTemperature", "Ambient Temperature")
                )

    async_add_entities(entities)


class GardenaBatterySensor(SensorEntity):
    """Representation of a Gardena battery sensor."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_battery"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} Battery Level"

    @property
    def native_value(self) -> float | None:
        """Return the battery level."""
        battery_data = self.device_data.get("attributes", {}).get("batteryLevel", {})
        return battery_data.get("value")

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return PERCENTAGE

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class GardenaTemperatureSensor(SensorEntity):
    """Representation of a Gardena temperature sensor."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        location_id: str,
        device_id: str,
        device_data: dict[str, Any],
        temp_attr: str,
        temp_name: str,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.location_id = location_id
        self.device_id = device_id
        self.device_data = device_data
        self.temp_attr = temp_attr
        self.temp_name = temp_name
        
        # Set unique ID
        self._attr_unique_id = f"{device_id}_{temp_attr}"
        
        # Set name
        device_name = device_data.get("attributes", {}).get("name", {}).get("value", "Unknown Device")
        self._attr_name = f"{device_name} {temp_name}"

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        temp_data = self.device_data.get("attributes", {}).get(self.temp_attr, {})
        return temp_data.get("value")

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success 