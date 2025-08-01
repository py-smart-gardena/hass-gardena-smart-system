"""Tests for Gardena Smart System data models."""
import pytest
from unittest.mock import Mock

from .models import (
    GardenaLocation,
    GardenaDevice,
    GardenaCommonService,
    GardenaMowerService,
    GardenaPowerSocketService,
    GardenaValveService,
    GardenaSensorService,
    GardenaDataParser,
)


class TestGardenaLocation:
    """Test GardenaLocation model."""

    def test_location_creation(self):
        """Test creating a GardenaLocation."""
        location = GardenaLocation(id="test-id", name="Test Garden")
        
        assert location.id == "test-id"
        assert location.name == "Test Garden"
        assert location.devices == {}

    def test_location_with_devices(self):
        """Test location with devices."""
        device = GardenaDevice(
            id="device-1",
            name="Test Device",
            model_type="Test Model",
            serial="12345",
            location_id="test-id"
        )
        location = GardenaLocation(id="test-id", name="Test Garden")
        location.devices["device-1"] = device
        
        assert len(location.devices) == 1
        assert location.devices["device-1"] == device


class TestGardenaDevice:
    """Test GardenaDevice model."""

    def test_device_creation(self):
        """Test creating a GardenaDevice."""
        device = GardenaDevice(
            id="device-1",
            name="Test Device",
            model_type="Test Model",
            serial="12345",
            location_id="test-id"
        )
        
        assert device.id == "device-1"
        assert device.name == "Test Device"
        assert device.model_type == "Test Model"
        assert device.serial == "12345"
        assert device.location_id == "test-id"
        assert device.services == {}

    def test_device_with_services(self):
        """Test device with services."""
        device = GardenaDevice(
            id="device-1",
            name="Test Device",
            model_type="Test Model",
            serial="12345",
            location_id="test-id"
        )
        
        common_service = GardenaCommonService(
            id="common-1",
            type="COMMON",
            device_id="device-1",
            battery_level=80
        )
        device.services["COMMON"] = common_service
        
        assert len(device.services) == 1
        assert device.services["COMMON"] == common_service


class TestGardenaServices:
    """Test Gardena service models."""

    def test_common_service(self):
        """Test GardenaCommonService."""
        service = GardenaCommonService(
            id="common-1",
            type="COMMON",
            device_id="device-1",
            name="Test Device",
            battery_level=80,
            battery_state="OK",
            rf_link_level=100,
            rf_link_state="ONLINE"
        )
        
        assert service.id == "common-1"
        assert service.type == "COMMON"
        assert service.device_id == "device-1"
        assert service.name == "Test Device"
        assert service.battery_level == 80
        assert service.battery_state == "OK"
        assert service.rf_link_level == 100
        assert service.rf_link_state == "ONLINE"

    def test_mower_service(self):
        """Test GardenaMowerService."""
        service = GardenaMowerService(
            id="mower-1",
            type="MOWER",
            device_id="device-1",
            state="OK",
            activity="PARKED_TIMER",
            operating_hours=1506
        )
        
        assert service.id == "mower-1"
        assert service.type == "MOWER"
        assert service.device_id == "device-1"
        assert service.state == "OK"
        assert service.activity == "PARKED_TIMER"
        assert service.operating_hours == 1506

    def test_power_socket_service(self):
        """Test GardenaPowerSocketService."""
        service = GardenaPowerSocketService(
            id="power-1",
            type="POWER_SOCKET",
            device_id="device-1",
            state="OK",
            activity="OFF",
            duration=3600
        )
        
        assert service.id == "power-1"
        assert service.type == "POWER_SOCKET"
        assert service.device_id == "device-1"
        assert service.state == "OK"
        assert service.activity == "OFF"
        assert service.duration == 3600

    def test_valve_service(self):
        """Test GardenaValveService."""
        service = GardenaValveService(
            id="valve-1",
            type="VALVE",
            device_id="device-1",
            name="Test Valve",
            state="OK",
            activity="CLOSED",
            duration=1800
        )
        
        assert service.id == "valve-1"
        assert service.type == "VALVE"
        assert service.device_id == "device-1"
        assert service.name == "Test Valve"
        assert service.state == "OK"
        assert service.activity == "CLOSED"
        assert service.duration == 1800

    def test_sensor_service(self):
        """Test GardenaSensorService."""
        service = GardenaSensorService(
            id="sensor-1",
            type="SENSOR",
            device_id="device-1",
            soil_humidity=45,
            soil_temperature=22.5,
            ambient_temperature=25.0,
            light_intensity=1000
        )
        
        assert service.id == "sensor-1"
        assert service.type == "SENSOR"
        assert service.device_id == "device-1"
        assert service.soil_humidity == 45
        assert service.soil_temperature == 22.5
        assert service.ambient_temperature == 25.0
        assert service.light_intensity == 1000


class TestGardenaDataParser:
    """Test GardenaDataParser."""

    def test_parse_locations_response(self):
        """Test parsing locations response."""
        response_data = {
            "data": [
                {
                    "id": "location-1",
                    "type": "LOCATION",
                    "attributes": {
                        "name": "Test Garden"
                    }
                }
            ]
        }
        
        locations = GardenaDataParser.parse_locations_response(response_data)
        
        assert len(locations) == 1
        assert locations[0].id == "location-1"
        assert locations[0].name == "Test Garden"

    def test_parse_location_response(self):
        """Test parsing location response with devices."""
        response_data = {
            "data": {
                "id": "location-1",
                "type": "LOCATION",
                "attributes": {
                    "name": "Test Garden"
                },
                "relationships": {
                    "devices": {
                        "data": [
                            {"id": "device-1", "type": "DEVICE"}
                        ]
                    }
                }
            },
            "included": [
                {
                    "id": "device-1",
                    "type": "DEVICE",
                    "relationships": {
                        "location": {
                            "data": {"id": "location-1", "type": "LOCATION"}
                        },
                        "services": {
                            "data": [
                                {"id": "common-1", "type": "COMMON"},
                                {"id": "mower-1", "type": "MOWER"}
                            ]
                        }
                    }
                },
                {
                    "id": "common-1",
                    "type": "COMMON",
                    "relationships": {
                        "device": {
                            "data": {"id": "device-1", "type": "DEVICE"}
                        }
                    },
                    "attributes": {
                        "name": {"value": "Test Mower"},
                        "batteryLevel": {"value": 80},
                        "batteryState": {"value": "OK"},
                        "modelType": {"value": "GARDENA smart Mower"},
                        "serial": {"value": "12345"},
                        "rfLinkState": {"value": "ONLINE"}
                    }
                },
                {
                    "id": "mower-1",
                    "type": "MOWER",
                    "relationships": {
                        "device": {
                            "data": {"id": "device-1", "type": "DEVICE"}
                        }
                    },
                    "attributes": {
                        "state": {"value": "OK"},
                        "activity": {"value": "PARKED_TIMER"},
                        "operatingHours": {"value": 1506}
                    }
                }
            ]
        }
        
        location = GardenaDataParser.parse_location_response(response_data)
        
        assert location.id == "location-1"
        assert location.name == "Test Garden"
        assert len(location.devices) == 1
        
        device = location.devices["device-1"]
        assert device.id == "device-1"
        assert device.name == "Test Mower"
        assert device.model_type == "GARDENA smart Mower"
        assert device.serial == "12345"
        assert len(device.services) == 2
        
        # Check COMMON service
        common_service = device.services["COMMON"]
        assert common_service.id == "common-1"
        assert common_service.type == "COMMON"
        assert common_service.battery_level == 80
        assert common_service.battery_state == "OK"
        assert common_service.rf_link_state == "ONLINE"
        
        # Check MOWER service
        mower_service = device.services["MOWER"]
        assert mower_service.id == "mower-1"
        assert mower_service.type == "MOWER"
        assert mower_service.state == "OK"
        assert mower_service.activity == "PARKED_TIMER"
        assert mower_service.operating_hours == 1506

    def test_parse_empty_locations_response(self):
        """Test parsing empty locations response."""
        response_data = {"data": []}
        locations = GardenaDataParser.parse_locations_response(response_data)
        assert len(locations) == 0

    def test_parse_location_response_no_devices(self):
        """Test parsing location response without devices."""
        response_data = {
            "data": {
                "id": "location-1",
                "type": "LOCATION",
                "attributes": {
                    "name": "Test Garden"
                },
                "relationships": {
                    "devices": {
                        "data": []
                    }
                }
            },
            "included": []
        }
        
        location = GardenaDataParser.parse_location_response(response_data)
        assert location.id == "location-1"
        assert location.name == "Test Garden"
        assert len(location.devices) == 0 