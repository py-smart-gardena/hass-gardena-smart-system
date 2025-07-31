"""Switch platform for Gardena Smart System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SERVICE_TYPE_POWER_SOCKET
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gardena Smart System switch platform."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    for device in coordinator.data.get("devices", []):
        if device.get("type") == SERVICE_TYPE_POWER_SOCKET:
            entities.append(
                GardenaPowerSocket(
                    coordinator,
                    device,
                )
            )

    async_add_entities(entities)


class GardenaPowerSocket(SwitchEntity):
    """Representation of a Gardena Smart System power socket."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = f"{device['id']}_switch"
        self._attr_name = device.get("attributes", {}).get("name", {}).get("value", "Gardena Power Socket")
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=self._attr_name,
            manufacturer="Gardena",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        activity = self.device.get("attributes", {}).get("activity", {}).get("value")
        return activity in ["FOREVER_ON", "TIME_LIMITED_ON", "SCHEDULED_ON"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        command_data = {
            "id": "turn_on",
            "type": "POWER_SOCKET_CONTROL",
            "attributes": {
                "command": "START_OVERRIDE",
            },
        }
        
        await self.coordinator.client.send_command(
            self.device["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        command_data = {
            "id": "turn_off",
            "type": "POWER_SOCKET_CONTROL",
            "attributes": {
                "command": "STOP_UNTIL_NEXT_TASK",
            },
        }
        
        await self.coordinator.client.send_command(
            self.device["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        ) 