"""Support for Gardena Smart System lawn mowers."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lawn_mower import LawnMowerEntity, LawnMowerActivity, LawnMowerEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN, MOWER_ACTIVITY_MAP
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System lawn mowers."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create lawn mower entities for each device
    entities = []
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(f"Checking device {device.name} ({device.id}) - Services: {list(device.services.keys())}")
            # Add lawn mower entities if available
            if "MOWER" in device.services:
                mower_services = device.services["MOWER"]
                _LOGGER.info(f"Found {len(mower_services)} mower services for device: {device.name} ({device.id})")
                for mower_service in mower_services:
                    _LOGGER.info(f"Creating lawn mower entity for service: {mower_service.id}")
                    entities.append(GardenaLawnMower(coordinator, device, mower_service))
            else:
                _LOGGER.debug(f"Device {device.name} ({device.id}) has no MOWER service")

    _LOGGER.info(f"Created {len(entities)} lawn mower entities")
    _LOGGER.info(f"Adding entities to Home Assistant: {[entity.name for entity in entities]}")
    async_add_entities(entities)
    _LOGGER.info("Lawn mower entities added to Home Assistant")
    
    # Register custom services
    platform = async_get_current_platform()
    
    # Start mowing for a specific duration
    platform.async_register_entity_service(
        "start_override",
        {
            vol.Required("duration"): cv.positive_int 
        },
        "async_start_override",
    )
    
    # Start mowing with automatic schedule
    platform.async_register_entity_service(
        "start_automatic",
        {},
        "async_start_automatic",
    )
    
    # Park until next scheduled task
    platform.async_register_entity_service(
        "park_until_next_task",
        {},
        "async_park_until_next_task",
    )
    
    # Park until further notice
    platform.async_register_entity_service(
        "park_until_further_notice",
        {},
        "async_park_until_further_notice",
    )


class GardenaLawnMower(GardenaEntity, LawnMowerEntity):
    """Representation of a Gardena lawn mower."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, mower_service) -> None:
        """Initialize the lawn mower."""
        super().__init__(coordinator, device, "MOWER")
        self._attr_name = f"{device.name} Lawn Mower"
        self._mower_service = mower_service
        self._attr_unique_id = f"{device.id}_mower"
        self._attr_supported_features = (
            LawnMowerEntityFeature.START_MOWING |
            LawnMowerEntityFeature.PAUSE |
            LawnMowerEntityFeature.DOCK
        )
        _LOGGER.info(f"Initialized lawn mower entity: {self._attr_name} with unique_id: {self._attr_unique_id} and features: {self._attr_supported_features}")
        _LOGGER.info(f"Mower service ID: {mower_service.id}, Device ID: {device.id}")
        _LOGGER.info(f"Supported features: START_MOWING={bool(self._attr_supported_features & LawnMowerEntityFeature.START_MOWING)}, PAUSE={bool(self._attr_supported_features & LawnMowerEntityFeature.PAUSE)}, DOCK={bool(self._attr_supported_features & LawnMowerEntityFeature.DOCK)}")

    @property
    def activity(self) -> LawnMowerActivity:
        """Return the current activity of the lawn mower."""
        if not self.available:
            _LOGGER.debug(f"Lawn mower {self._attr_name} not available")
            return LawnMowerActivity.ERROR
        
        mower_service = self._mower_service
        if not mower_service:
            _LOGGER.debug(f"Lawn mower {self._attr_name} has no mower service")
            return LawnMowerActivity.ERROR
        
        activity = mower_service.activity
        mapped_activity = MOWER_ACTIVITY_MAP.get(activity, LawnMowerActivity.ERROR)
        _LOGGER.debug(f"Lawn mower {self._attr_name} activity: {activity} -> {mapped_activity}")
        return mapped_activity

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        
        mower_service = self._mower_service
        if mower_service:
            attrs.update({
                "operating_hours": mower_service.operating_hours,
                "state": mower_service.state,
                "activity": mower_service.activity,
                "last_error_code": getattr(mower_service, 'last_error_code', None),
                "device_id": self.device.id,
                "service_id": mower_service.id,
            })
        
        return attrs

    def start_mowing(self) -> None:
        """Start mowing - synchronous wrapper."""
        raise NotImplementedError("Use async_start_mowing instead")

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        _LOGGER.info(f"=== START_MOWING called for {self._attr_name} ===")
        _LOGGER.info(f"Starting mowing for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "start_mowing",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "START_DONT_OVERRIDE",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self._mower_service.id, command_data)
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== START_MOWING completed for {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error in start_mowing for {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No mower service available for {self._attr_name}")

    def pause(self) -> None:
        """Pause mowing - synchronous wrapper."""
        raise NotImplementedError("Use async_pause instead")

    async def async_pause(self) -> None:
        """Pause mowing."""
        _LOGGER.info(f"=== PAUSE called for {self._attr_name} ===")
        _LOGGER.info(f"Pausing mowing for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "pause_mowing",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "PARK_UNTIL_FURTHER_NOTICE",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self._mower_service.id, command_data)
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== PAUSE completed for {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error in pause for {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No mower service available for {self._attr_name}")

    def dock(self) -> None:
        """Dock the mower - synchronous wrapper."""
        raise NotImplementedError("Use async_dock instead")

    async def async_dock(self) -> None:
        """Dock the mower."""
        _LOGGER.info(f"=== DOCK called for {self._attr_name} ===")
        _LOGGER.info(f"Docking mower {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "dock_mower",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "PARK_UNTIL_NEXT_TASK",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self._mower_service.id, command_data)
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== DOCK completed for {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error in dock for {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No mower service available for {self._attr_name}")

    async def async_start_override(self, duration: int) -> None:
        """Start mowing for a specific duration."""
        _LOGGER.info(f"Starting mowing for {duration} seconds for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "start_override",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "START_SECONDS_TO_OVERRIDE",
                        "seconds": duration,
                    },
                }
            }
            await self.coordinator.client.send_command(self._mower_service.id, command_data)
            await self.coordinator.async_request_refresh()

    async def async_start_automatic(self) -> None:
        """Start mowing with automatic schedule."""
        _LOGGER.info(f"Starting automatic mowing for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "start_automatic",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "START_DONT_OVERRIDE",
                    },
                }
            }
            await self.coordinator.client.send_command(self._mower_service.id, command_data)
            await self.coordinator.async_request_refresh()

    async def async_park_until_next_task(self) -> None:
        """Park the mower until the next scheduled task."""
        _LOGGER.info(f"Parking mower until next task for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "park_next_task",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "PARK_UNTIL_NEXT_TASK",
                    },
                }
            }
            await self.coordinator.client.send_command(self._mower_service.id, command_data)
            await self.coordinator.async_request_refresh()

    async def async_park_until_further_notice(self) -> None:
        """Park the mower until further notice."""
        _LOGGER.info(f"Parking mower until further notice for {self.device.name} ({self._mower_service.id})")
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "park_further_notice",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "PARK_UNTIL_FURTHER_NOTICE",
                    },
                }
            }
            await self.coordinator.client.send_command(self._mower_service.id, command_data)
            await self.coordinator.async_request_refresh() 