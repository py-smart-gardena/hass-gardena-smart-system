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
            for valve_service in device.services.get("VALVE", []):
                entities.append(GardenaValveProblemSensor(coordinator, device, valve_service))

    entities.append(GardenaWebSocketConnectedSensor(coordinator, entry.entry_id))

    async_add_entities(entities)


class GardenaOnlineBinarySensor(GardenaOnlineEntity, BinarySensorEntity):
    """Representation of a Gardena device online status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the online status sensor."""
        super().__init__(coordinator, device)
        self._keep_entity_id("binary_sensor", f"{device.name} Online")


class GardenaWebSocketConnectedSensor(GardenaEntity, BinarySensorEntity):
    """Binary sensor indicating whether the Gardena WebSocket is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "websocket_connected"

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
        self._attr_unique_id = f"gardena_websocket_connected_{entry_id}"
        self._keep_entity_id("binary_sensor", "Gardena WebSocket Connected")

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



# The service states in which the API asks to look at lastErrorCode.
_VALVE_PROBLEM_STATES = ("WARNING", "ERROR")


class GardenaValveProblemSensor(GardenaEntity, BinarySensorEntity):
    """On when a valve reports a problem (#408).

    One standard signal for automations and dashboards, next to the error
    sensor that says which. It follows the valve's state: the API asks to
    look at lastErrorCode when the state is WARNING ("automatic operation
    might be impaired") or ERROR ("automatic operation is impossible"). An
    error code alone can stay from an earlier run while the valve is fine,
    so it is reported as an attribute, not as a problem.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the valve problem sensor."""
        super().__init__(coordinator, device, "VALVE")
        self._valve_service = valve_service
        self._device_id = device.id
        self._name_per_valve("valve_problem", valve_service)
        self._keep_entity_id(
            "binary_sensor", f"{valve_service.name or device.name} Problem"
        )
        self._attr_unique_id = f"{device.id}_{valve_service.id}_problem"

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self._valve_service.id:
                    return service
        return None

    @property
    def available(self) -> bool:
        """Unavailable where no valve is connected, like the valve itself (#409)."""
        if not super().available:
            return False
        current_service = self._get_current_valve_service()
        return not (current_service and current_service.state == "UNAVAILABLE")

    @property
    def is_on(self) -> bool | None:
        """Return True when the valve reports WARNING or ERROR."""
        current_service = self._get_current_valve_service()
        if not current_service or not current_service.state:
            return None
        return current_service.state in _VALVE_PROBLEM_STATES

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the valve's state and error code."""
        attrs = super().extra_state_attributes
        current_service = self._get_current_valve_service()
        if current_service:
            attrs["state"] = current_service.state
            error_code = current_service.last_error_code
            attrs["error_code"] = error_code.lower() if error_code else None
        return attrs
