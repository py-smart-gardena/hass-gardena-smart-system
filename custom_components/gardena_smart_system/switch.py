"""Support for Gardena Smart System switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System switches."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create switch entities for each device
    entities = []
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(f"Checking device {device.name} ({device.id}) - Services: {list(device.services.keys())}")
            # Add power socket switches if available
            if "POWER_SOCKET" in device.services:
                power_services = device.services["POWER_SOCKET"]
                _LOGGER.debug(f"Found {len(power_services)} power socket services for device: {device.name} ({device.id})")
                for power_service in power_services:
                    _LOGGER.debug(f"Creating power socket switch for service: {power_service.id}")
                    entities.append(GardenaPowerSocketSwitch(coordinator, device, power_service))
            else:
                _LOGGER.debug(f"Device {device.name} ({device.id}) has no POWER_SOCKET service")

            _LOGGER.debug(f"Created {len(entities)} power socket switch entities")
    async_add_entities(entities)


class GardenaPowerSocketSwitch(GardenaDeviceEntity, SwitchEntity):
    """Representation of a Gardena power socket switch."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, power_service) -> None:
        """Initialize the power socket switch."""
        super().__init__(coordinator, device, "POWER_SOCKET")
        self._attr_name = f"{device.name} Power Socket"
        self._power_service = power_service

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if self._power_service and self._power_service.activity:
            return self._power_service.activity in ["FOREVER_ON", "TIME_LIMITED_ON", "SCHEDULED_ON"]
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._power_service:
            command_data = {
                "data": {
                    "id": "turn_on",
                    "type": "POWER_SOCKET_CONTROL",
                    "attributes": {
                        "command": "START_OVERRIDE",
                    },
                }
            }
            await self.coordinator.client.send_command(self._power_service.id, command_data)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._power_service:
            command_data = {
                "data": {
                    "id": "turn_off",
                    "type": "POWER_SOCKET_CONTROL",
                    "attributes": {
                        "command": "STOP_UNTIL_NEXT_TASK",
                    },
                }
            }
            await self.coordinator.client.send_command(self._power_service.id, command_data)
            await self.coordinator.async_request_refresh() 