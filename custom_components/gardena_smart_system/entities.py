"""Base entity classes for Gardena Smart System."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice

_LOGGER = logging.getLogger(__name__)


class GardenaEntity(CoordinatorEntity, ABC):
    """Base class for Gardena entities."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: GardenaDevice,
        service_type: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.device = device
        self.service_type = service_type
        self._attr_unique_id = f"{device.id}_{service_type}"
        self._attr_name = self._get_entity_name()
        self._attr_device_info = self._get_device_info()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if coordinator is working and WebSocket is connected
        if not self.coordinator.last_update_success:
            return False
        
        # Check WebSocket connection status
        if self.coordinator.websocket_client:
            if self.coordinator.websocket_client.connection_status != "connected":
                return False
        
        # Check if device exists in coordinator data
        for location in self.coordinator.locations.values():
            if self.device.id in location.devices:
                device = location.devices[self.device.id]
                # Check if device has COMMON service and is online
                if "COMMON" in device.services and device.services["COMMON"]:
                    common_service = device.services["COMMON"][0]
                    if common_service and common_service.rf_link_state:
                        return common_service.rf_link_state == "ONLINE"
                return True  # Device exists but no COMMON service, assume available
        return False

    def _get_entity_name(self) -> str:
        """Get the entity name."""
        device_name = self.device.name or "Unknown Device"
        service_name = self._get_service_display_name()
        return f"{device_name} {service_name}"

    def _get_service_display_name(self) -> str:
        """Get display name for the service type."""
        service_names = {
            "COMMON": "Status",
            "MOWER": "Lawn Mower",
            "POWER_SOCKET": "Power Socket",
            "VALVE": "Valve",
            "VALVE_SET": "Valve Set",
            "SENSOR": "Sensor",
        }
        return service_names.get(self.service_type, self.service_type.title())

    def _get_device_info(self) -> DeviceInfo:
        """Get device info for this entity."""
        common_service = None
        if "COMMON" in self.device.services and self.device.services["COMMON"]:
            # Get the first COMMON service (there should only be one per device)
            common_service = self.device.services["COMMON"][0]
        
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.id)},
            name=self.device.name,
            manufacturer="Gardena",
            model=common_service.model_type if common_service else "Unknown Model",
            serial_number=common_service.serial if common_service else self.device.serial,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = {}
        
        # Add battery information if available
        if "COMMON" in self.device.services and self.device.services["COMMON"]:
            common_service = self.device.services["COMMON"][0]
            if common_service and common_service.battery_level is not None:
                attrs["battery_level"] = common_service.battery_level
            if common_service and common_service.battery_state:
                attrs["battery_state"] = common_service.battery_state
            if common_service and common_service.rf_link_level is not None:
                attrs["rf_link_level"] = common_service.rf_link_level
            if common_service and common_service.rf_link_state:
                attrs["rf_link_state"] = common_service.rf_link_state
        
        return attrs


class GardenaDeviceEntity(GardenaEntity):
    """Base class for device-specific entities."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: GardenaDevice,
        service_type: str,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device, service_type)
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Get device info."""
        return self._get_device_info()


class GardenaServiceEntity(GardenaEntity):
    """Base class for service-specific entities."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: GardenaDevice,
        service_type: str,
    ) -> None:
        """Initialize the service entity."""
        super().__init__(coordinator, device, service_type)
        self._attr_has_entity_name = False  # Service entities don't have their own name

    @property
    def device_info(self) -> DeviceInfo:
        """Get device info."""
        return self._get_device_info()


class GardenaBatteryEntity(GardenaEntity):
    """Base class for Gardena battery entities."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the battery entity."""
        super().__init__(coordinator, device, "COMMON")

    @property
    def battery_level(self) -> int | None:
        """Return the battery level."""
        if "COMMON" in self.device.services and self.device.services["COMMON"]:
            common_service = self.device.services["COMMON"][0]
            return common_service.battery_level
        return None

    @property
    def battery_state(self) -> str | None:
        """Return the battery state."""
        if "COMMON" in self.device.services and self.device.services["COMMON"]:
            common_service = self.device.services["COMMON"][0]
            return common_service.battery_state
        return None


class GardenaOnlineEntity(GardenaEntity):
    """Base class for Gardena online status entities."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device) -> None:
        """Initialize the online entity."""
        super().__init__(coordinator, device, "COMMON")

    @property
    def is_on(self) -> bool:
        """Return true if device is online."""
        if "COMMON" in self.device.services and self.device.services["COMMON"]:
            common_service = self.device.services["COMMON"][0]
            return common_service.rf_link_state == "ONLINE"
        return False 