"""Support for Gardena Smart System binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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

    entities = []

    for location in coordinator.locations.values():
        for device in location.devices.values():
            entities.append(GardenaOnlineBinarySensor(coordinator, device))

    entities.append(GardenaWebSocketConnectedSensor(coordinator, entry.entry_id))

    async_add_entities(entities)


class GardenaOnlineBinarySensor(GardenaOnlineEntity, BinarySensorEntity):
    """Representation of a Gardena device online status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the online status sensor."""
        super().__init__(coordinator, device)
        self._attr_name = f"{device.name} Online"


class GardenaWebSocketConnectedSensor(GardenaEntity, BinarySensorEntity):
    """Binary sensor indicating whether the Gardena WebSocket is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, entry_id: str) -> None:
        """Initialize the WebSocket connectivity sensor."""
        from .models import GardenaDevice
        dummy_device = GardenaDevice(
            id=f"websocket_status_{entry_id}",
            name="WebSocket Status",
            model_type="WebSocket Client",
            serial="websocket",
            services={},
            location_id=""
        )
        super().__init__(coordinator, dummy_device, "WEBSOCKET")
        self._attr_name = "Gardena WebSocket Connected"
        self._attr_unique_id = f"gardena_websocket_connected_{entry_id}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True if WebSocket is connected."""
        if self.coordinator.websocket_client:
            return self.coordinator.websocket_client.is_connected
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        if self.coordinator.websocket_client:
            attrs.update({
                "reconnect_attempts": self.coordinator.websocket_client.reconnect_attempts,
            })
        return attrs

