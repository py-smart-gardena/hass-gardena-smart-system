"""Support for Gardena Smart System sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_BATTERY_STATE,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
)
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System sensors."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create sensor entities for each device
    entities = []
    
    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(f"Checking device {device.name} ({device.id}) - Services: {list(device.services.keys())}")
            
            # Add battery sensors if available
            if "COMMON" in device.services:
                common_services = device.services["COMMON"]
                _LOGGER.debug(f"Found {len(common_services)} common services for device: {device.name} ({device.id})")
                for common_service in common_services:
                    _LOGGER.debug(f"Creating battery sensor for service: {common_service.id}")
                    entities.append(GardenaBatterySensor(coordinator, device, common_service))
            
            # Add sensor entities if available
            if "SENSOR" in device.services:
                sensor_services = device.services["SENSOR"]
                _LOGGER.debug(f"Found {len(sensor_services)} sensor services for device: {device.name} ({device.id})")
                for sensor_service in sensor_services:
                    _LOGGER.debug(f"Creating sensor entities for service: {sensor_service.id}")
                    
                    # Check if this is a soil sensor (has soil_humidity or soil_temperature)
                    is_soil_sensor = (sensor_service.soil_humidity is not None or 
                                    sensor_service.soil_temperature is not None)
                    
                    # Create temperature sensors
                    if sensor_service.soil_temperature is not None:
                        entities.append(GardenaTemperatureSensor(coordinator, device, sensor_service, "soil_temperature", is_soil_sensor))
                    if sensor_service.ambient_temperature is not None:
                        entities.append(GardenaTemperatureSensor(coordinator, device, sensor_service, "ambient_temperature", is_soil_sensor))
                    
                    # Create humidity sensor (only for soil sensors)
                    if sensor_service.soil_humidity is not None:
                        entities.append(GardenaHumiditySensor(coordinator, device, sensor_service))
                    
                    # Create light sensor (only for non-soil sensors)
                    if sensor_service.light_intensity is not None and not is_soil_sensor:
                        entities.append(GardenaLightSensor(coordinator, device, sensor_service))

    # Add WebSocket status sensor
    entities.append(GardenaWebSocketStatusSensor(coordinator))

            _LOGGER.debug(f"Created {len(entities)} sensor entities")
    async_add_entities(entities)


class GardenaBatterySensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena battery sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, common_service) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, device, "COMMON")
        self._common_service = common_service
        self._attr_name = f"{device.name} Battery Level"
        self._attr_unique_id = f"{device.id}_{common_service.id}_battery_level"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_icon = "mdi:battery"

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        return self._common_service.battery_level

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            ATTR_BATTERY_STATE: self._common_service.battery_state,
            ATTR_RF_LINK_LEVEL: self._common_service.rf_link_level,
            ATTR_RF_LINK_STATE: self._common_service.rf_link_state,
        })
        return attrs


class GardenaTemperatureSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena temperature sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service, temp_attr: str, is_soil_sensor: bool = False) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._temp_attr = temp_attr
        
        if temp_attr == "soil_temperature":
            self._attr_name = f"{device.name} Soil Temperature"
            self._attr_unique_id = f"{device.id}_{sensor_service.id}_soil_temperature"
        else:
            self._attr_name = f"{device.name} Ambient Temperature"
            self._attr_unique_id = f"{device.id}_{sensor_service.id}_ambient_temperature"
        
        # Add soil sensor indicator to name if it's a soil sensor
        if is_soil_sensor and temp_attr == "soil_temperature":
            self._attr_name = f"{device.name} Soil Temperature (Soil Sensor)"
        
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> int | None:
        """Return the temperature value."""
        if self._temp_attr == "soil_temperature":
            return self._sensor_service.soil_temperature
        else:
            return self._sensor_service.ambient_temperature


class GardenaHumiditySensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena humidity sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._attr_name = f"{device.name} Soil Humidity"
        self._attr_unique_id = f"{device.id}_{sensor_service.id}_soil_humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_icon = "mdi:water-percent"

    @property
    def native_value(self) -> int | None:
        """Return the humidity value."""
        return self._sensor_service.soil_humidity


class GardenaLightSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena light sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service) -> None:
        """Initialize the light sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._attr_name = f"{device.name} Light Intensity"
        self._attr_unique_id = f"{device.id}_{sensor_service.id}_light_intensity"
        self._attr_native_unit_of_measurement = "lux"
        self._attr_device_class = SensorDeviceClass.ILLUMINANCE
        self._attr_icon = "mdi:white-balance-sunny"

    @property
    def native_value(self) -> int | None:
        """Return the light intensity value."""
        return self._sensor_service.light_intensity


class GardenaWebSocketStatusSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena WebSocket status sensor."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator) -> None:
        """Initialize the WebSocket status sensor."""
        # Create a dummy device for the base entity
        from .models import GardenaDevice
        dummy_device = GardenaDevice(
            id="websocket_status",
            name="WebSocket Status",
            model_type="WebSocket Client",
            serial="websocket",
            services={},
            location_id=""
        )
        
        super().__init__(coordinator, dummy_device, "WEBSOCKET")
        self._attr_name = "Gardena WebSocket Status"
        self._attr_unique_id = "gardena_websocket_status"
        self._attr_icon = "mdi:connection"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # WebSocket status sensor is always available
        return True

    @property
    def native_value(self) -> str:
        """Return the WebSocket connection status."""
        if self.coordinator.websocket_client:
            status = self.coordinator.websocket_client.connection_status
            _LOGGER.debug(f"WebSocket status sensor: client available, status={status}")
            return status
        _LOGGER.debug("WebSocket status sensor: client not available")
        return "disconnected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        
        # Add reconnect button when disconnected
        if self.native_value == "disconnected":
            attrs["reconnect_button"] = True
            attrs["reconnect_service"] = "gardena_smart_system.reconnect_websocket"
        
        if self.coordinator.websocket_client:
            attrs.update({
                "reconnect_attempts": self.coordinator.websocket_client.reconnect_attempts,
                "is_connected": self.coordinator.websocket_client.is_connected,
                "is_connecting": self.coordinator.websocket_client.is_connecting,
            })
        
        return attrs

 