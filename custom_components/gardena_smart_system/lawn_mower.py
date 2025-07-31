"""Lawn mower platform for Gardena Smart System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    DEVICE_TYPE_MOWER,
    SERVICE_TYPE_MOWER,
    MOWER_STATE_OK,
    MOWER_STATE_WARNING,
    MOWER_STATE_ERROR,
    MOWER_STATE_UNAVAILABLE,
    MOWER_ACTIVITY_CUTTING,
    MOWER_ACTIVITY_SEARCHING,
    MOWER_ACTIVITY_LEAVING,
    MOWER_ACTIVITY_CHARGING,
    MOWER_ACTIVITY_PARKED,
)
from .coordinator import GardenaSmartSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gardena Smart System lawn mower platform."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    for device in coordinator.data.get("devices", []):
        if device.get("type") == DEVICE_TYPE_MOWER:
            # Find the mower service for this device
            device_id = device.get("id")
            mower_service = None
            
            for service in coordinator.data.get("devices", []):
                if (
                    service.get("type") == SERVICE_TYPE_MOWER
                    and service.get("relationships", {}).get("device", {}).get("data", {}).get("id") == device_id
                ):
                    mower_service = service
                    break
            
            if mower_service:
                entities.append(
                    GardenaLawnMower(
                        coordinator,
                        device,
                        mower_service,
                    )
                )

    async_add_entities(entities)


class GardenaLawnMower(LawnMowerEntity):
    """Representation of a Gardena Smart System lawn mower."""

    def __init__(
        self,
        coordinator: GardenaSmartSystemCoordinator,
        device: dict[str, Any],
        mower_service: dict[str, Any],
    ) -> None:
        """Initialize the lawn mower."""
        self.coordinator = coordinator
        self.device = device
        self.mower_service = mower_service
        self._attr_unique_id = f"{device['id']}_mower"
        self._attr_name = device.get("attributes", {}).get("name", {}).get("value", "Gardena Mower")
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=self._attr_name,
            manufacturer="Gardena",
            model=device.get("attributes", {}).get("modelType", {}).get("value", "Unknown"),
            serial_number=device.get("attributes", {}).get("serial", {}).get("value"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current activity of the lawn mower."""
        activity = self.mower_service.get("attributes", {}).get("activity", {}).get("value")
        
        if activity == MOWER_ACTIVITY_CUTTING:
            return LawnMowerActivity.MOWING
        elif activity == MOWER_ACTIVITY_SEARCHING:
            return LawnMowerActivity.SEARCHING
        elif activity == MOWER_ACTIVITY_LEAVING:
            return LawnMowerActivity.LEAVING
        elif activity == MOWER_ACTIVITY_CHARGING:
            return LawnMowerActivity.CHARGING
        elif activity == MOWER_ACTIVITY_PARKED:
            return LawnMowerActivity.PARKED
        else:
            return None

    @property
    def state(self) -> str | None:
        """Return the current state of the lawn mower."""
        return self.mower_service.get("attributes", {}).get("state", {}).get("value")

    @property
    def supported_features(self) -> LawnMowerEntityFeature:
        """Return the supported features."""
        return (
            LawnMowerEntityFeature.START_MOWING
            | LawnMowerEntityFeature.PAUSE
            | LawnMowerEntityFeature.DOCK
        )

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        command_data = {
            "id": "start_mowing",
            "type": "MOWER_CONTROL",
            "attributes": {
                "command": "START_DONT_OVERRIDE",
            },
        }
        
        await self.coordinator.client.send_command(
            self.mower_service["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        """Pause mowing."""
        command_data = {
            "id": "pause_mowing",
            "type": "MOWER_CONTROL",
            "attributes": {
                "command": "PARK_UNTIL_NEXT_TASK",
            },
        }
        
        await self.coordinator.client.send_command(
            self.mower_service["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_dock(self) -> None:
        """Dock the mower."""
        command_data = {
            "id": "dock_mower",
            "type": "MOWER_CONTROL",
            "attributes": {
                "command": "PARK_UNTIL_FURTHER_NOTICE",
            },
        }
        
        await self.coordinator.client.send_command(
            self.mower_service["id"], command_data
        )
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        ) 