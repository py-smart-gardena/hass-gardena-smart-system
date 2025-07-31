"""Valve platform for Gardena Smart System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SERVICE_TYPE_VALVE
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gardena Smart System valve platform."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    for device in coordinator.data.get("devices", []):
        if device.get("type") == SERVICE_TYPE_VALVE:
            entities.append(
                GardenaValve(
                    coordinator,
                    device,
                )
            )

    async_add_entities(entities)


class GardenaValve(ValveEntity):
    """Representation of a Gardena Smart System valve."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the valve."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = f"{device['id']}_valve"
        self._attr_name = device.get("attributes", {}).get("name", {}).get("value", "Gardena Valve")
        
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
    def is_closed(self) -> bool | None:
        """Return true if the valve is closed."""
        activity = self.device.get("attributes", {}).get("activity", {}).get("value")
        return activity == "CLOSED"

    @property
    def supported_features(self) -> ValveEntityFeature:
        """Return the supported features."""
        return ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        command_data = {
            "id": "open_valve",
            "type": "VALVE_CONTROL",
            "attributes": {
                "command": "START_SECONDS_TO_OVERRIDE",
                "seconds": 3600,  # Default 1 hour
            },
        }
        
        await self.coordinator.client.send_command(
            self.device["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        command_data = {
            "id": "close_valve",
            "type": "VALVE_CONTROL",
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