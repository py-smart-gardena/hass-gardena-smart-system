"""Support for Gardena Smart System sensors."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_BATTERY_STATE,
    ATTR_RF_LINK_LEVEL,
    ATTR_RF_LINK_STATE,
    MOWER_INFORMATIONAL_CODES,
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
            
            # Add battery and RF link sensors for devices that have COMMON service
            if "COMMON" in device.services:
                common_services = device.services["COMMON"]
                _LOGGER.debug(f"Found {len(common_services)} common services for device: {device.name} ({device.id})")
                for common_service in common_services:
                    # Only create battery sensor if device has a battery.
                    # Include when battery_level is present even if battery_state is not yet
                    # populated (soil sensors can return null battery_state at initial load).
                    has_battery = (
                        common_service.battery_state not in [None, "NO_BATTERY"]
                        or common_service.battery_level is not None
                    )
                    if has_battery:
                        _LOGGER.debug(f"Creating battery sensor for device with battery: {device.name} (battery_state: {common_service.battery_state})")
                        entities.append(GardenaBatterySensor(coordinator, device, common_service))
                    else:
                        _LOGGER.debug(f"Skipping battery sensor for device without battery: {device.name} (battery_state: {common_service.battery_state})")

                    # RF Link Quality sensor
                    if common_service.rf_link_level is not None:
                        entities.append(GardenaRFLinkLevelSensor(coordinator, device, common_service))
            
            # Add mower sensors
            if "MOWER" in device.services:
                mower_services = device.services["MOWER"]
                for mower_service in mower_services:
                    entities.append(GardenaMowerErrorSensor(coordinator, device, mower_service))
                    if mower_service.operating_hours is not None:
                        entities.append(GardenaMowerOperatingHoursSensor(coordinator, device, mower_service))

            # Add watering end time sensors for valves
            if "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                for valve_service in valve_services:
                    entities.append(GardenaValveRemainingTimeSensor(coordinator, device, valve_service))

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
                    
                    # Create light sensor
                    if sensor_service.light_intensity is not None:
                        entities.append(GardenaLightSensor(coordinator, device, sensor_service))

    # Add API usage diagnostic sensor (one per config entry)
    entities.append(GardenaAPIUsageSensor(coordinator, entry.entry_id))

    _LOGGER.debug(f"Created {len(entities)} sensor entities")
    async_add_entities(entities)


class GardenaBatterySensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena battery sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, common_service) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, device, "COMMON")
        self._common_service = common_service
        self._device_id = device.id
        self._attr_name = f"{device.name} Battery Level"
        self._attr_unique_id = f"{device.id}_{common_service.id}_battery_level"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_icon = "mdi:battery"

    def _get_current_common_service(self):
        """Get current common service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "COMMON" in device.services:
            for service in device.services["COMMON"]:
                if service.id == self._common_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        current_service = self._get_current_common_service()
        return current_service.battery_level if current_service else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        current_service = self._get_current_common_service()
        if current_service:
            attrs.update({
                ATTR_BATTERY_STATE: current_service.battery_state,
                ATTR_RF_LINK_LEVEL: current_service.rf_link_level,
                ATTR_RF_LINK_STATE: current_service.rf_link_state,
            })
        return attrs


class GardenaMowerErrorSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena mower error code sensor."""

    _attr_translation_key = "mower_error"
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, mower_service) -> None:
        """Initialize the mower error sensor."""
        super().__init__(coordinator, device, "MOWER")
        self._mower_service = mower_service
        self._device_id = device.id
        self._attr_name = None
        self._attr_unique_id = f"{device.id}_{mower_service.id}_last_error_code"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_options = [
            "uninitialised", "no_message", "outside_working_area", "no_loop_signal",
            "no_charging_station_signal", "wrong_loop_signal",
            "loop_sensor_problem_front", "loop_sensor_problem_rear",
            "trapped", "upside_down", "low_battery", "empty_battery", "no_drive",
            "lifted", "stuck_in_charging_station", "charging_station_blocked",
            "collision_sensor_problem_rear", "collision_sensor_problem_front",
            "wheel_motor_blocked_right", "wheel_motor_blocked_left",
            "wheel_drive_problem_right", "wheel_drive_problem_left",
            "cutting_system_blocked", "invalid_sub_device_combination",
            "settings_restored", "charging_system_problem", "tilt_sensor_problem",
            "mower_tilted", "wheel_motor_overloaded_right",
            "wheel_motor_overloaded_left", "charging_current_too_high",
            "electronic_problem", "cutting_height_blocked", "cutting_height_problem",
            "temporary_problem", "guide_1_not_found", "guide_2_not_found",
            "guide_3_not_found", "gps_tracker_module_error", "weak_gps_signal",
            "guide_calibration_failed", "temporary_battery_problem",
            "battery_problem", "alarm_mower_switched_off", "alarm_mower_stopped",
            "alarm_mower_lifted", "alarm_mower_tilted", "com_board_not_available",
            "slipped", "invalid_battery_combination", "safety_function_faulty",
            "invalid_system_conf", "lift_sensor_defect", "mobile_loop_defect",
            "left_loop_sensor", "right_loop_sensor", "wrong_pin", "temporary_lift",
            "cutting_drive", "steep_slope", "stop_button_fail",
            "angle_cutting_means_off", "slave_mcu_lost", "cutting_overload",
            "cutting_height_range", "cutting_height_drift", "cutting_height_limited",
            "cutting_height_drive", "cutting_height_current",
            "cutting_height_direction", "mower_to_cs_com", "ultrasonic_error",
            "high_low_bat_temp_a", "high_low_bat_temp_b",
            "too_low_voltage_bat_a", "too_low_voltage_bat_b",
            "alarm_motion", "alarm_geofence",
            "rr_wheel_blocked", "rl_wheel_blocked",
            "rr_wheel_drive", "rl_wheel_drive",
            "rear_right_wheel_overloaded", "rear_left_wheel_overloaded",
            "angular_sensor_defect", "no_power_in_cs", "switch_cord_sensor_defect",
            "map_not_valid", "no_position", "no_rs_communication",
            "folding_sensor_activated",
            "ultrasonic_sensor_1_defect", "ultrasonic_sensor_2_defect",
            "ultrasonic_sensor_3_defect", "ultrasonic_sensor_4_defect",
            "cutting_drive_motor_1_defect", "cutting_drive_motor_2_defect",
            "cutting_drive_motor_3_defect",
            "collision_sensor_defect", "docking_sensor_defect",
            "folding_cutting_deck_sensor_defect", "loop_sensor_defect",
            "collision_sensor_error", "no_confirmed_position",
            "major_cutting_disk_imbalance", "complex_working_area",
            "invalid_sw_configuration", "radar_error", "work_area_tampered",
            "destination_not_reachable", "wait_stop_pressed", "wait_for_safety_pin",
            "destination_not_reachable_warning", "battery_near_end_of_life",
            "edgemotor_blocked", "no_correction_data", "invalid_correction_data",
            "wait_updating", "wait_power_up", "off_disabled", "off_hatch_open",
            "off_hatch_closed", "parked_daily_limit_reached",
            "vision_system_malfunction", "poor_vision_system_performance",
            "vision_processing_failed",
            "loop_sensor_problem_left", "loop_sensor_problem_right",
            "wrong_pin_code", "lost_wheel_brush", "accessory_power_anomaly",
            "loop_wire_broken", "battery_fet_error", "imbalanced_cutting_disc",
            "cutting_motor_problem", "limited_cutting_height_range",
            "cutting_motor_drive_defect", "memory_circuit_problem",
            "stop_button_problem", "difficult_finding_home",
            "guide_calibration_accomplished", "too_many_batteries",
            "alarm_mower_in_motion", "alarm_outside_geofence",
            "connection_changed", "connection_not_changed",
            "unknown",
        ]

    def _get_current_mower_service(self):
        """Get current mower service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "MOWER" in device.services:
            for service in device.services["MOWER"]:
                if service.id == self._mower_service.id:
                    return service
        return None

    @property
    def native_value(self) -> str | None:
        """Return the last error code, or 'no_message' for informational states."""
        current_service = self._get_current_mower_service()
        if not current_service:
            return None
        error_code = current_service.last_error_code
        if error_code:
            code = error_code.lower()
            if code in MOWER_INFORMATIONAL_CODES:
                return "no_message"
            return code
        return "no_message"

    @property
    def icon(self) -> str:
        """Return icon based on error state."""
        value = self.native_value
        if value and value != "no_message":
            return "mdi:alert-circle"
        return "mdi:check-circle-outline"


class GardenaMowerOperatingHoursSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena mower operating hours sensor."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, mower_service) -> None:
        """Initialize the operating hours sensor."""
        super().__init__(coordinator, device, "MOWER")
        self._mower_service = mower_service
        self._device_id = device.id
        self._attr_name = f"{device.name} Operating Hours"
        self._attr_unique_id = f"{device.id}_{mower_service.id}_operating_hours"
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._attr_icon = "mdi:clock-outline"

    def _get_current_mower_service(self):
        """Get current mower service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "MOWER" in device.services:
            for service in device.services["MOWER"]:
                if service.id == self._mower_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the operating hours."""
        current_service = self._get_current_mower_service()
        return current_service.operating_hours if current_service else None


class GardenaRFLinkLevelSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena RF link quality sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, common_service) -> None:
        """Initialize the RF link level sensor."""
        super().__init__(coordinator, device, "COMMON")
        self._common_service = common_service
        self._device_id = device.id
        self._attr_name = f"{device.name} RF Link Quality"
        self._attr_unique_id = f"{device.id}_{common_service.id}_rf_link_level"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:signal"

    def _get_current_common_service(self):
        """Get current common service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "COMMON" in device.services:
            for service in device.services["COMMON"]:
                if service.id == self._common_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the RF link level."""
        current_service = self._get_current_common_service()
        return current_service.rf_link_level if current_service else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        current_service = self._get_current_common_service()
        if current_service:
            attrs[ATTR_RF_LINK_STATE] = current_service.rf_link_state
        return attrs


class GardenaTemperatureSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena temperature sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service, temp_attr: str, is_soil_sensor: bool = False) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._device_id = device.id
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

    def _get_current_sensor_service(self):
        """Get current sensor service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "SENSOR" in device.services:
            for service in device.services["SENSOR"]:
                if service.id == self._sensor_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the temperature value."""
        current_service = self._get_current_sensor_service()
        if not current_service:
            return None
            
        if self._temp_attr == "soil_temperature":
            return current_service.soil_temperature
        else:
            return current_service.ambient_temperature


class GardenaHumiditySensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena humidity sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._device_id = device.id
        self._attr_name = f"{device.name} Soil Humidity"
        self._attr_unique_id = f"{device.id}_{sensor_service.id}_soil_humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.MOISTURE
        self._attr_icon = "mdi:water-percent"

    def _get_current_sensor_service(self):
        """Get current sensor service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "SENSOR" in device.services:
            for service in device.services["SENSOR"]:
                if service.id == self._sensor_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the humidity value."""
        current_service = self._get_current_sensor_service()
        return current_service.soil_humidity if current_service else None


class GardenaLightSensor(GardenaEntity, SensorEntity):
    """Representation of a Gardena light sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, sensor_service) -> None:
        """Initialize the light sensor."""
        super().__init__(coordinator, device, "SENSOR")
        self._sensor_service = sensor_service
        self._device_id = device.id
        self._attr_name = f"{device.name} Light Intensity"
        self._attr_unique_id = f"{device.id}_{sensor_service.id}_light_intensity"
        self._attr_native_unit_of_measurement = "lx"
        self._attr_device_class = SensorDeviceClass.ILLUMINANCE
        self._attr_icon = "mdi:white-balance-sunny"

    def _get_current_sensor_service(self):
        """Get current sensor service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "SENSOR" in device.services:
            for service in device.services["SENSOR"]:
                if service.id == self._sensor_service.id:
                    return service
        return None

    @property
    def native_value(self) -> int | None:
        """Return the light intensity value."""
        current_service = self._get_current_sensor_service()
        return current_service.light_intensity if current_service else None


class GardenaValveRemainingTimeSensor(GardenaEntity, SensorEntity):
    """Sensor that shows the watering end time for a valve."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the valve remaining time sensor."""
        super().__init__(coordinator, device, "VALVE")
        self._valve_service = valve_service
        self._device_id = device.id
        valve_name = valve_service.name or device.name
        self._attr_name = f"{valve_name} Watering End"
        self._attr_unique_id = f"{device.id}_{valve_service.id}_watering_end"
        self._attr_icon = "mdi:timer-sand"

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self._device_id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self._valve_service.id:
                    return service
        return None

    @property
    def native_value(self) -> datetime | None:
        """Return the watering end timestamp."""
        current_service = self._get_current_valve_service()
        if not current_service:
            return None

        if current_service.activity in ("MANUAL_WATERING", "SCHEDULED_WATERING"):
            if current_service.duration and current_service.duration_timestamp:
                try:
                    start = datetime.fromisoformat(
                        current_service.duration_timestamp.replace("Z", "+00:00")
                    )
                    return start + timedelta(seconds=current_service.duration)
                except (ValueError, TypeError):
                    return None
        return None


class GardenaAPIUsageSensor(SensorEntity):
    """Sensor tracking Gardena API usage against the 700 requests/week quota."""

    _attr_has_entity_name = True
    _attr_translation_key = "api_requests_week"
    _attr_icon = "mdi:api"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, entry_id: str) -> None:
        """Initialize the API usage sensor."""
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"gardena_api_usage_{entry_id}"
        self._attr_name = "API Requests (Week)"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"websocket_status_{entry_id}")},
        )

    @property
    def available(self) -> bool:
        """Always available."""
        return True

    @property
    def native_value(self) -> int:
        """Return the number of API requests this week."""
        return self.coordinator.client.api_tracker.requests_this_week

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes with request breakdown."""
        tracker = self.coordinator.client.api_tracker
        attrs: dict[str, Any] = {
            "requests_today": tracker.requests_today,
            "requests_this_week": tracker.requests_this_week,
            "quota_weekly": 700,
            "requests_by_endpoint": tracker.requests_by_endpoint(),
            "recent_requests": tracker.recent_requests,
        }
        return attrs

    async def async_update(self) -> None:
        """No-op: value is computed on read from the shared tracker."""


