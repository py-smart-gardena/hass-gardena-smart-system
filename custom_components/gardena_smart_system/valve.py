"""Support for Gardena Smart System valves."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature, ValveDeviceClass
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
    """Set up Gardena Smart System valves."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create valve entities for each device
    entities = []
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(f"Checking device {device.name} ({device.id}) - Model: {getattr(device, 'model_type', 'Unknown')} - Services: {list(device.services.keys())}")
            
            # Check if this is a Water Control (single valve device)
            if device.model_type == "WATER_CONTROL" and "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                if len(valve_services) == 1:
                    _LOGGER.info(f"Found Water Control device: {device.name} ({device.id})")
                    entities.append(GardenaWaterControl(coordinator, device, valve_services[0]))
                else:
                    _LOGGER.warning(f"Water Control device {device.name} has {len(valve_services)} valve services, expected 1")
            
            # Check if this is a Smart Irrigation Control (multiple valve device)
            elif device.model_type == "SMART_IRRIGATION_CONTROL" and "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                _LOGGER.info(f"Found Smart Irrigation Control device: {device.name} ({device.id}) with {len(valve_services)} valves")
                for valve_service in valve_services:
                    _LOGGER.info(f"Creating valve entity for Smart Irrigation Control: {valve_service.name} ({valve_service.id})")
                    entities.append(GardenaSmartIrrigationControl(coordinator, device, valve_service))
            
            # Fallback for other devices with VALVE services
            elif "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                _LOGGER.info(f"Found generic device with valves: {device.name} ({device.id}) with {len(valve_services)} valves")
                for valve_service in valve_services:
                    _LOGGER.info(f"Creating generic valve entity: {valve_service.name} ({valve_service.id})")
                    entities.append(GardenaValve(coordinator, device, valve_service))

    _LOGGER.info(f"Created {len(entities)} valve entities")
    async_add_entities(entities)


class GardenaWaterControl(GardenaEntity, ValveEntity):
    """Representation of a Gardena Water Control (single valve device)."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the Water Control."""
        super().__init__(coordinator, device, "VALVE")
        self.valve_service = valve_service
        self._attr_name = device.name  # Use device name, not service name
        self._attr_unique_id = f"{device.id}_water_control"
        
        # Set required attributes for valve entities
        self._attr_reports_position = False
        self._attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        self._attr_device_class = ValveDeviceClass.WATER

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            is_closed = current_service.activity == "CLOSED"
            _LOGGER.debug(f"Water Control {self.device.name} activity: {current_service.activity} -> is_closed: {is_closed}")
            return is_closed
        _LOGGER.debug(f"Water Control {self.device.name} has no activity data -> assuming closed")
        return True

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self.device.id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self.valve_service.id:
                    return service
        return None

    @property
    def is_open(self) -> bool:
        """Return true if valve is open (watering)."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            # According to API: MANUAL_WATERING or SCHEDULED_WATERING means valve is open
            is_open = current_service.activity in ["MANUAL_WATERING", "SCHEDULED_WATERING"]
            _LOGGER.debug(f"Water Control {self.device.name} activity: {current_service.activity} -> is_open: {is_open}")
            return is_open
        _LOGGER.debug(f"Water Control {self.device.name} has no activity data -> assuming closed")
        return False

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        return False

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        return False

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"=== OPEN_VALVE called for Water Control {self.device.name} ===")
        _LOGGER.info(f"Opening Water Control {self.device.name} ({self.valve_service.id})")
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "open_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "START_SECONDS_TO_OVERRIDE",
                        "seconds": 3600,  # Default 1 hour
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self.valve_service.id, command_data)
                _LOGGER.info(f"Command sent successfully, requesting refresh")
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== OPEN_VALVE completed for Water Control {self.device.name} ===")
            except Exception as e:
                _LOGGER.error(f"Error opening Water Control {self.device.name}: {e}")
                raise
        else:
            _LOGGER.error(f"No valve service available for Water Control {self.device.name}")

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"=== CLOSE_VALVE called for Water Control {self.device.name} ===")
        _LOGGER.info(f"Closing Water Control {self.device.name} ({self.valve_service.id})")
        _LOGGER.info(f"Current valve state - is_open: {self.is_open}, is_closed: {self.is_closed}, activity: {self.valve_service.activity if self.valve_service else 'None'}")
        
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "close_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "STOP_UNTIL_NEXT_TASK",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self.valve_service.id, command_data)
                _LOGGER.info(f"Command sent successfully, requesting refresh")
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== CLOSE_VALVE completed for Water Control {self.device.name} ===")
            except Exception as e:
                _LOGGER.error(f"Error closing Water Control {self.device.name}: {e}")
                raise
        else:
            _LOGGER.error(f"No valve service available for Water Control {self.device.name}")


class GardenaSmartIrrigationControl(GardenaEntity, ValveEntity):
    """Representation of a Gardena Smart Irrigation Control valve (multiple valve device)."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the Smart Irrigation Control valve."""
        super().__init__(coordinator, device, "VALVE")
        self.valve_service = valve_service
        self._attr_name = f"{device.name} - {valve_service.name}"
        self._attr_unique_id = f"{device.id}_{valve_service.id}"
        
        # Set required attributes for valve entities
        self._attr_reports_position = False
        self._attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        self._attr_device_class = ValveDeviceClass.WATER

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            is_closed = current_service.activity == "CLOSED"
            _LOGGER.info(f"Smart Irrigation Control valve {self._attr_name} activity: {current_service.activity} -> is_closed: {is_closed}")
            return is_closed
        _LOGGER.info(f"Smart Irrigation Control valve {self._attr_name} has no activity data -> assuming closed")
        return True

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self.device.id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self.valve_service.id:
                    return service
        return None

    @property
    def is_open(self) -> bool:
        """Return true if valve is open (watering)."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            # According to API: MANUAL_WATERING or SCHEDULED_WATERING means valve is open
            is_open = current_service.activity in ["MANUAL_WATERING", "SCHEDULED_WATERING"]
            _LOGGER.info(f"Smart Irrigation Control valve {self._attr_name} activity: {current_service.activity} -> is_open: {is_open}")
            return is_open
        _LOGGER.info(f"Smart Irrigation Control valve {self._attr_name} has no activity data -> assuming closed")
        return False

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        return False

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        return False

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"=== OPEN_VALVE called for Smart Irrigation Control valve {self._attr_name} ===")
        _LOGGER.info(f"Opening Smart Irrigation Control valve {self._attr_name} ({self.valve_service.id})")
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "open_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "START_SECONDS_TO_OVERRIDE",
                        "seconds": 3600,  # Default 1 hour
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self.valve_service.id, command_data)
                _LOGGER.info(f"Command sent successfully, requesting refresh")
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== OPEN_VALVE completed for Smart Irrigation Control valve {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error opening Smart Irrigation Control valve {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No valve service available for Smart Irrigation Control valve {self._attr_name}")

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"=== CLOSE_VALVE called for Smart Irrigation Control valve {self._attr_name} ===")
        _LOGGER.info(f"Closing Smart Irrigation Control valve {self._attr_name} ({self.valve_service.id})")
        _LOGGER.info(f"Current valve state - is_open: {self.is_open}, is_closed: {self.is_closed}, activity: {self.valve_service.activity if self.valve_service else 'None'}")
        
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "close_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "STOP_UNTIL_NEXT_TASK",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self.valve_service.id, command_data)
                _LOGGER.info(f"Command sent successfully, requesting refresh")
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== CLOSE_VALVE completed for Smart Irrigation Control valve {self._attr_name} ===")
            except Exception as e:
                _LOGGER.error(f"Error closing Smart Irrigation Control valve {self._attr_name}: {e}")
                raise
        else:
            _LOGGER.error(f"No valve service available for Smart Irrigation Control valve {self._attr_name}")


class GardenaValve(GardenaEntity, ValveEntity):
    """Representation of a Gardena valve."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the valve."""
        super().__init__(coordinator, device, "VALVE")
        self.valve_service = valve_service
        self._attr_name = valve_service.name
        self._attr_unique_id = f"{device.id}_{valve_service.id}"
        
        # Set required attributes for valve entities
        self._attr_reports_position = False
        self._attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            is_closed = current_service.activity == "CLOSED"
            _LOGGER.info(f"Valve {current_service.name} activity: {current_service.activity} -> is_closed: {is_closed}")
            return is_closed
        _LOGGER.info(f"Valve has no activity data -> assuming closed")
        return True

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self.device.id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self.valve_service.id:
                    return service
        return None

    @property
    def is_open(self) -> bool:
        """Return true if valve is open (watering)."""
        # Get fresh data from coordinator
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            # According to API: MANUAL_WATERING or SCHEDULED_WATERING means valve is open
            is_open = current_service.activity in ["MANUAL_WATERING", "SCHEDULED_WATERING"]
            _LOGGER.info(f"Valve {current_service.name} activity: {current_service.activity} -> is_open: {is_open}")
            return is_open
        _LOGGER.info(f"Valve has no activity data -> assuming closed")
        return False

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        # API doesn't provide intermediate opening state, return False
        # Valve goes directly from CLOSED to WATERING
        return False

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        # API doesn't provide intermediate closing state, return False
        # Valve goes directly from WATERING to CLOSED
        return False

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"Opening valve {self.valve_service.name} ({self.valve_service.id})")
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "open_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "START_SECONDS_TO_OVERRIDE",
                        "seconds": 3600,  # Default 1 hour
                    },
                }
            }
            await self.coordinator.client.send_command(self.valve_service.id, command_data)
            await self.coordinator.async_request_refresh()

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"=== CLOSE_VALVE called for {self.valve_service.name} ===")
        _LOGGER.info(f"Closing valve {self.valve_service.name} ({self.valve_service.id})")
        _LOGGER.info(f"Current valve state - is_open: {self.is_open}, is_closed: {self.is_closed}, activity: {self.valve_service.activity if self.valve_service else 'None'}")
        
        if self.valve_service:
            command_data = {
                "data": {
                    "id": "close_valve",
                    "type": "VALVE_CONTROL",
                    "attributes": {
                        "command": "STOP_UNTIL_NEXT_TASK",
                    },
                }
            }
            _LOGGER.info(f"Sending command: {command_data}")
            try:
                await self.coordinator.client.send_command(self.valve_service.id, command_data)
                _LOGGER.info(f"Command sent successfully, requesting refresh")
                await self.coordinator.async_request_refresh()
                _LOGGER.info(f"=== CLOSE_VALVE completed for {self.valve_service.name} ===")
            except Exception as e:
                _LOGGER.error(f"Error closing valve {self.valve_service.name}: {e}")
                raise
        else:
            _LOGGER.error(f"No valve service available for {self.valve_service.name}")
