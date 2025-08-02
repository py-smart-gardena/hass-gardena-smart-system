"""Data coordinator for Gardena Smart System."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .gardena_client import GardenaSmartSystemClient
from .models import GardenaLocation
from .websocket_client import GardenaWebSocketClient

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemCoordinator(DataUpdateCoordinator[Dict[str, GardenaLocation]]):
    """Gardena Smart System Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, client: GardenaSmartSystemClient) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.locations: Dict[str, GardenaLocation] = {}
        self.websocket_client: GardenaWebSocketClient | None = None
        self._initial_data_loaded = False
        
        # Set update interval to None to disable periodic updates
        # All updates will come through WebSocket
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # Disable periodic updates
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data for the first time only."""
        if not self._initial_data_loaded:
            await super().async_config_entry_first_refresh()
            self._initial_data_loaded = True
            
            # Start WebSocket client after first data fetch
            await self._start_websocket()
        else:
            # For subsequent calls, just return current data
            self.async_set_updated_data(self.locations)

    async def _start_websocket(self) -> None:
        """Start WebSocket client for real-time events."""
        try:
            if not self.websocket_client:
                self.websocket_client = GardenaWebSocketClient(
                    auth_manager=self.client.auth_manager,
                    event_callback=self._handle_websocket_event,
                    hass=self.hass,
                    coordinator=self,
                )
            
            await self.websocket_client.start()
            _LOGGER.info("WebSocket client started successfully")
            
            # Notify entities that WebSocket client is now available
            self.async_set_updated_data(self.locations)
            
        except Exception as e:
            _LOGGER.error(f"Failed to start WebSocket client: {e}")

    async def _handle_websocket_event(self, event: Dict[str, Any]) -> None:
        """Handle WebSocket events."""
        try:
            event_type = event.get("type")
            
            if event_type == "service_update":
                await self._process_service_update(event)
            elif event_type == "device_event":
                await self._process_device_event(event["data"])
            else:
                _LOGGER.debug(f"Unknown event type: {event_type}")
                
        except Exception as e:
            _LOGGER.error(f"Error handling WebSocket event: {e}")

    async def _process_service_update(self, event: Dict[str, Any]) -> None:
        """Process service update from WebSocket."""
        try:
            # Extract service information
            service_id = event.get("service_id")
            service_type = event.get("service_type")
            device_id = event.get("device_id")
            event_data = event.get("data", {})
            
            _LOGGER.debug(f"Processing service update: service_id={service_id}, device_id={device_id}, type={service_type}")
            _LOGGER.debug(f"Event data: {event_data}")
            
            if not device_id or not service_id:
                _LOGGER.debug("Service update missing device_id or service_id")
                return
            
            # Update the specific device/service in our data
            await self._update_device_from_event(device_id, service_id, service_type, event_data)
            
            # Notify listeners of data update
            self.async_set_updated_data(self.locations)
            
            _LOGGER.debug(f"Updated {service_type} service {service_id} for device {device_id} via WebSocket")
            
        except Exception as e:
            _LOGGER.error(f"Error processing service update: {e}")

    async def _process_device_event(self, event_data: Dict[str, Any]) -> None:
        """Process device event from WebSocket."""
        try:
            # Extract device and service information
            device_id = event_data.get("device_id")
            service_id = event_data.get("service_id")
            service_type = event_data.get("service_type")
            
            if not device_id or not service_id:
                _LOGGER.debug("Event missing device_id or service_id")
                return
            
            # Update the specific device/service in our data
            await self._update_device_from_event(device_id, service_id, service_type, event_data)
            
            # Notify listeners of data update
            self.async_set_updated_data(self.locations)
            
        except Exception as e:
            _LOGGER.error(f"Error processing device event: {e}")

    async def _update_device_from_event(self, device_id: str, service_id: str, service_type: str, event_data: Dict[str, Any]) -> None:
        """Update device data from WebSocket event."""
        try:
            # Find the device in our locations
            for location in self.locations.values():
                if device_id in location.devices:
                    device = location.devices[device_id]
                    
                    # Update the specific service
                    if service_type in device.services:
                        services = device.services[service_type]
                        for service in services:
                            if service.id == service_id:
                                # Update service attributes based on event data
                                await self._update_service_attributes(service, event_data)
                                _LOGGER.debug(f"Updated {service_type} service {service_id} for device {device_id}")
                                return
                    
                    _LOGGER.debug(f"Service {service_id} not found for device {device_id}")
                    return
            
            _LOGGER.debug(f"Device {device_id} not found in locations")
            
        except Exception as e:
            _LOGGER.error(f"Error updating device from event: {e}")

    async def _update_service_attributes(self, service: Any, event_data: Dict[str, Any]) -> None:
        """Update service attributes from event data."""
        try:
            # Helper function to extract value from WebSocket data structure
            def extract_value(data, key):
                if key in data:
                    value_data = data[key]
                    if isinstance(value_data, dict) and 'value' in value_data:
                        return value_data['value']
                    return value_data
                return None
            
            # Update common attributes
            if hasattr(service, 'state') and 'state' in event_data:
                service.state = extract_value(event_data, 'state')
            
            if hasattr(service, 'activity') and 'activity' in event_data:
                service.activity = extract_value(event_data, 'activity')
            
            # Update service-specific attributes
            if hasattr(service, 'battery_level') and 'batteryLevel' in event_data:
                service.battery_level = extract_value(event_data, 'batteryLevel')
            
            if hasattr(service, 'battery_state') and 'batteryState' in event_data:
                service.battery_state = extract_value(event_data, 'batteryState')
            
            if hasattr(service, 'rf_link_state') and 'rfLinkState' in event_data:
                service.rf_link_state = extract_value(event_data, 'rfLinkState')
            
            if hasattr(service, 'rf_link_level') and 'rfLinkLevel' in event_data:
                service.rf_link_level = extract_value(event_data, 'rfLinkLevel')
            
            # Update mower-specific attributes
            if hasattr(service, 'operating_hours') and 'operatingHours' in event_data:
                service.operating_hours = extract_value(event_data, 'operatingHours')
            
            if hasattr(service, 'last_error_code') and 'lastErrorCode' in event_data:
                service.last_error_code = extract_value(event_data, 'lastErrorCode')
            
            # Update sensor-specific attributes
            if hasattr(service, 'soil_humidity') and 'soilHumidity' in event_data:
                service.soil_humidity = extract_value(event_data, 'soilHumidity')
            
            if hasattr(service, 'soil_temperature') and 'soilTemperature' in event_data:
                service.soil_temperature = extract_value(event_data, 'soilTemperature')
            
            if hasattr(service, 'ambient_temperature') and 'ambientTemperature' in event_data:
                service.ambient_temperature = extract_value(event_data, 'ambientTemperature')
            
            if hasattr(service, 'light_intensity') and 'lightIntensity' in event_data:
                service.light_intensity = extract_value(event_data, 'lightIntensity')
                
        except Exception as e:
            _LOGGER.error(f"Error updating service attributes: {e}")

    async def _async_update_data(self) -> Dict[str, GardenaLocation]:
        """Update data from Gardena Smart System - only called once at startup."""
        _LOGGER.debug("Starting initial data load from Gardena Smart System")
        
        try:
            # Fetch locations only once at startup
            locations_list = await self.client.get_locations()
            
            # Convert list to dictionary and get detailed location data
            for location in locations_list:
                try:
                    # Get detailed location with devices
                    detailed_location = await self.client.get_location(location.id)
                    self.locations[location.id] = detailed_location
                    _LOGGER.debug(f"Loaded location {location.id} with {len(detailed_location.devices)} devices")
                except Exception as e:
                    _LOGGER.warning(f"Failed to get devices for location {location.id}: {e}")
                    # Keep the basic location info even if device fetch fails
                    self.locations[location.id] = location
            
            _LOGGER.info("Initial data load completed. All future updates will come via WebSocket.")
            return self.locations
            
        except Exception as e:
            _LOGGER.error(f"Error loading initial data: {e}")
            raise

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.debug("Shutting down Gardena Smart System coordinator")
        
        # Stop WebSocket client
        if self.websocket_client:
            await self.websocket_client.stop()
            self.websocket_client = None
        
        # Close client
        if self.client:
            await self.client.close()

    def get_devices_by_type(self, device_type: str) -> list:
        """Get all devices of a specific type."""
        devices = []
        for location in self.locations.values():
            for device in location.devices.values():
                if device_type in device.services:
                    devices.append(device)
        return devices

    def get_device_by_id(self, device_id: str) -> Any | None:
        """Get a device by its ID."""
        for location in self.locations.values():
            if device_id in location.devices:
                return location.devices[device_id]
        return None 