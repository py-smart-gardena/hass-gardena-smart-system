"""Data models for Gardena Smart System."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GardenaLocation:
    """Represents a Gardena location."""
    
    id: str
    name: str
    devices: Dict[str, GardenaDevice] = None
    
    def __post_init__(self):
        if self.devices is None:
            self.devices = {}


@dataclass
class GardenaDevice:
    """Representation of a Gardena device."""
    id: str
    name: str
    model_type: str
    serial: str
    services: Dict[str, List[Any]]  # Changed from Dict[str, Any] to Dict[str, List[Any]]
    location_id: str
    
    def __post_init__(self):
        if self.services is None:
            self.services = {}


@dataclass
class GardenaService:
    """Base class for Gardena services."""
    
    id: str
    type: str
    device_id: str
    state: Optional[str] = None
    last_error_code: Optional[str] = None


@dataclass
class GardenaCommonService(GardenaService):
    """Common service properties shared across all devices."""
    
    name: Optional[str] = None
    battery_level: Optional[int] = None
    battery_state: Optional[str] = None
    rf_link_level: Optional[int] = None
    rf_link_state: Optional[str] = None
    model_type: Optional[str] = None
    serial: Optional[str] = None


@dataclass
class GardenaMowerService(GardenaService):
    """Mower service."""
    
    activity: Optional[str] = None
    operating_hours: Optional[int] = None


@dataclass
class GardenaPowerSocketService(GardenaService):
    """Power socket service."""
    
    activity: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class GardenaValveService(GardenaService):
    """Valve service."""
    
    name: Optional[str] = None
    activity: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class GardenaValveSetService(GardenaService):
    """Valve set service."""
    
    pass


@dataclass
class GardenaSensorService(GardenaService):
    """Sensor service."""
    
    soil_humidity: Optional[int] = None
    soil_temperature: Optional[float] = None
    ambient_temperature: Optional[float] = None
    light_intensity: Optional[int] = None


class GardenaDataParser:
    """Parser for Gardena API responses."""
    
    @staticmethod
    def parse_locations_response(data: Dict[str, Any]) -> List[GardenaLocation]:
        """Parse locations response from API."""
        locations = []
        
        for location_data in data.get("data", []):
            location = GardenaLocation(
                id=location_data["id"],
                name=location_data["attributes"]["name"]
            )
            locations.append(location)
        
        return locations
    
    @staticmethod
    def parse_location_response(data: Dict[str, Any]) -> GardenaLocation:
        """Parse location response with devices from API."""
        location_data = data["data"]
        location = GardenaLocation(
            id=location_data["id"],
            name=location_data["attributes"]["name"]
        )
        
        # Parse devices and services from included data
        devices = {}
        services = {}
        
        # First pass: create devices and collect service data
        for item in data.get("included", []):
            if item["type"] == "DEVICE":
                device = GardenaDevice(
                    id=item["id"],
                    name="",  # Will be filled from COMMON service
                    model_type="",  # Will be filled from COMMON service
                    serial="",  # Will be filled from COMMON service
                    services={},  # Will be filled with lists of services
                    location_id=location.id
                )
                devices[item["id"]] = device
            elif item["type"] in ["MOWER", "POWER_SOCKET", "VALVE", "VALVE_SET", "SENSOR", "COMMON"]:
                # Store service data for later processing
                service_type = item["type"]
                if service_type not in services:
                    services[service_type] = []
                services[service_type].append(item)
        
        # Second pass: associate services with devices
        for service_type, service_list in services.items():
            for service_data in service_list:
                device_id = service_data["relationships"]["device"]["data"]["id"]
                if device_id in devices:
                    device = devices[device_id]
                    if service_type not in device.services:
                        device.services[service_type] = []
                    device.services[service_type].append(
                        GardenaDataParser._create_service(service_type, service_data)
                    )
                    
                    # Update device info from COMMON service
                    if service_type == "COMMON":
                        attrs = service_data.get("attributes", {})
                        device.name = attrs.get("name", {}).get("value", device.name)
                        device.model_type = attrs.get("modelType", {}).get("value", device.model_type)
                        device.serial = attrs.get("serial", {}).get("value", device.serial)
        
        location.devices = devices
        return location

    @staticmethod
    def _create_service(service_type: str, service_data: Dict[str, Any]) -> Any:
        """Create a service object based on the service type."""
        service_id = service_data["id"]
        device_id = service_data["relationships"]["device"]["data"]["id"]
        attrs = service_data.get("attributes", {})
        
        if service_type == "COMMON":
            return GardenaCommonService(
                id=service_id,
                type="COMMON",
                device_id=device_id,
                name=attrs.get("name", {}).get("value"),
                battery_level=attrs.get("batteryLevel", {}).get("value"),
                battery_state=attrs.get("batteryState", {}).get("value"),
                rf_link_level=attrs.get("rfLinkLevel", {}).get("value"),
                rf_link_state=attrs.get("rfLinkState", {}).get("value"),
                model_type=attrs.get("modelType", {}).get("value"),
                serial=attrs.get("serial", {}).get("value")
            )
        elif service_type == "MOWER":
            return GardenaMowerService(
                id=service_id,
                type="MOWER",
                device_id=device_id,
                state=attrs.get("state", {}).get("value"),
                activity=attrs.get("activity", {}).get("value"),
                operating_hours=attrs.get("operatingHours", {}).get("value"),
                last_error_code=attrs.get("lastErrorCode", {}).get("value")
            )
        elif service_type == "POWER_SOCKET":
            return GardenaPowerSocketService(
                id=service_id,
                type="POWER_SOCKET",
                device_id=device_id,
                state=attrs.get("state", {}).get("value"),
                activity=attrs.get("activity", {}).get("value"),
                duration=attrs.get("duration", {}).get("value"),
                last_error_code=attrs.get("lastErrorCode", {}).get("value")
            )
        elif service_type == "VALVE":
            return GardenaValveService(
                id=service_id,
                type="VALVE",
                device_id=device_id,
                name=attrs.get("name", {}).get("value"),
                state=attrs.get("state", {}).get("value"),
                activity=attrs.get("activity", {}).get("value"),
                duration=attrs.get("duration", {}).get("value"),
                last_error_code=attrs.get("lastErrorCode", {}).get("value")
            )
        elif service_type == "VALVE_SET":
            return GardenaValveSetService(
                id=service_id,
                type="VALVE_SET",
                device_id=device_id,
                state=attrs.get("state", {}).get("value"),
                last_error_code=attrs.get("lastErrorCode", {}).get("value")
            )
        elif service_type == "SENSOR":
            return GardenaSensorService(
                id=service_id,
                type="SENSOR",
                device_id=device_id,
                soil_humidity=attrs.get("soilHumidity", {}).get("value"),
                soil_temperature=attrs.get("soilTemperature", {}).get("value"),
                ambient_temperature=attrs.get("ambientTemperature", {}).get("value"),
                light_intensity=attrs.get("lightIntensity", {}).get("value")
            )
        else:
            # Fallback for unknown service types
            return GardenaService(
                id=service_id,
                type=service_type,
                device_id=device_id
            ) 