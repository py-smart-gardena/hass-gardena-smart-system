"""Support for Gardena Smart System buttons."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System buttons."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create button entities for each mower device
    entities = []
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(f"Checking device {device.name} ({device.id}) for button entities - Services: {list(device.services.keys())}")
            # Add buttons if device has MOWER service
            if "MOWER" in device.services:
                mower_services = device.services["MOWER"]
                _LOGGER.info(f"Found {len(mower_services)} mower services for device: {device.name} ({device.id})")
                for mower_service in mower_services:
                    _LOGGER.info(f"Creating button entities for mower service: {mower_service.id}")
                    # Start Override button (immediate mowing)
                    entities.append(GardenaStartOverrideButton(coordinator, device, mower_service))
                    # Return to Dock button
                    entities.append(GardenaReturnToDockButton(coordinator, device, mower_service))
            else:
                _LOGGER.debug(f"Device {device.name} ({device.id}) has no MOWER service")

    _LOGGER.info(f"Created {len(entities)} button entities")
    _LOGGER.info(f"Adding button entities to Home Assistant: {[entity.name for entity in entities]}")
    async_add_entities(entities)
    _LOGGER.info("Button entities added to Home Assistant")


class GardenaStartOverrideButton(GardenaEntity, ButtonEntity):
    """Representation of a Gardena Start Override button."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, mower_service) -> None:
        """Initialize the Gardena Start Override button."""
        super().__init__(coordinator, device, "MOWER")
        self._attr_name = f"{device.name} Start Mowing Now"
        self._mower_service = mower_service
        self._attr_unique_id = f"{device.id}_start_override"
        self._attr_icon = "mdi:play"
        _LOGGER.info(f"Initialized start override button: {self._attr_name} with unique_id: {self._attr_unique_id}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        
        mower_service = self._mower_service
        if mower_service:
            attrs.update({
                "device_id": self.device.id,
                "service_id": mower_service.id,
                "button_type": "start_override",
                "description": "Start mowing immediately for 180 minutes (3 hours)",
            })
        
        return attrs

    async def async_press(self) -> None:
        """Handle the button press - Start mowing immediately."""
        _LOGGER.info(f"=== START OVERRIDE button pressed for {self._attr_name} ===")
        _LOGGER.info(f"Starting immediate mowing for {self.device.name} ({self._mower_service.id})")
        
        if self._mower_service:
            # Default to 180 minutes (10800 seconds) for immediate mowing
            duration = 10800  # 180 minutes (3 hours) in seconds
            command_data = {
                "data": {
                    "id": "start_override_button",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "START_SECONDS_TO_OVERRIDE",
                        "seconds": duration,
                    },
                }
            }
            _LOGGER.info(f"Sending start override command: {command_data}")
            try:
                await self.coordinator.client.send_command(self._mower_service.id, command_data)
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== START OVERRIDE button action completed for {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error in start override button for {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No mower service available for {self._attr_name}")


class GardenaReturnToDockButton(GardenaEntity, ButtonEntity):
    """Representation of a Gardena Return to Dock button."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, mower_service) -> None:
        """Initialize the Gardena Return to Dock button."""
        super().__init__(coordinator, device, "MOWER")
        self._attr_name = f"{device.name} Return to Dock"
        self._mower_service = mower_service
        self._attr_unique_id = f"{device.id}_return_to_dock"
        self._attr_icon = "mdi:home"
        _LOGGER.info(f"Initialized return to dock button: {self._attr_name} with unique_id: {self._attr_unique_id}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        
        mower_service = self._mower_service
        if mower_service:
            attrs.update({
                "device_id": self.device.id,
                "service_id": mower_service.id,
                "button_type": "return_to_dock",
                "description": "Return to dock and resume schedule",
            })
        
        return attrs

    async def async_press(self) -> None:
        """Handle the button press - Return to dock."""
        _LOGGER.info(f"=== RETURN TO DOCK button pressed for {self._attr_name} ===")
        _LOGGER.info(f"Returning to dock for {self.device.name} ({self._mower_service.id})")
        
        if self._mower_service:
            command_data = {
                "data": {
                    "id": "return_to_dock_button",
                    "type": "MOWER_CONTROL",
                    "attributes": {
                        "command": "PARK_UNTIL_NEXT_TASK",
                    },
                }
            }
            _LOGGER.info(f"Sending return to dock command: {command_data}")
            try:
                await self.coordinator.client.send_command(self._mower_service.id, command_data)
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== RETURN TO DOCK button action completed for {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error in return to dock button for {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No mower service available for {self._attr_name}")
