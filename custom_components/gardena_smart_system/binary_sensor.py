"""Binary sensor platform for Gardena Smart System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gardena Smart System binary sensor platform."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    # Add binary sensors based on device states
    for device in coordinator.data.get("devices", []):
        if device.get("type") == "DEVICE":
            # Add online/offline status
            entities.append(
                GardenaOnlineSensor(
                    coordinator,
                    device,
                )
            )

    async_add_entities(entities)


class GardenaOnlineSensor(BinarySensorEntity):
    """Representation of a Gardena device online status."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = f"{device['id']}_online"
        self._attr_name = f"{device.get('attributes', {}).get('name', {}).get('value', 'Gardena Device')} Online"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("attributes", {}).get("name", {}).get("value", "Gardena Device"),
            manufacturer="Gardena",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        # Check if device is online based on RF link state
        for service in self.coordinator.data.get("devices", []):
            if (
                service.get("type") == "COMMON"
                and service.get("relationships", {}).get("device", {}).get("data", {}).get("id") == self.device["id"]
            ):
                rf_state = service.get("attributes", {}).get("rfLinkState", {}).get("value")
                return rf_state == "ONLINE"
        return None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        ) 