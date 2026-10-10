"""Tests for Gardena Smart System entities."""
import pytest
from unittest.mock import Mock, AsyncMock

from .entities import (
    GardenaEntity,
    GardenaDeviceEntity,
    GardenaServiceEntity,
    GardenaBatteryEntity,
    GardenaOnlineEntity,
)
from .models import GardenaDevice, GardenaCommonService, GardenaMowerService
from .coordinator import GardenaSmartSystemCoordinator


class TestGardenaEntity:
    """Test GardenaEntity base class."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_device(self):
        """Create a mock device."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        device.name = "Test Device"
        device.model_type = "Test Model"
        device.serial = "12345"
        device.location_id = "test-location-1"
        device.services = {}
        return device

    def test_entity_initialization(self, mock_coordinator, mock_device):
        """Test entity initialization."""
        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")
        
        assert entity.device == mock_device
        assert entity.service_type == "MOWER"
        assert entity._attr_unique_id == "test-device-1_MOWER"
        assert entity._attr_name == "Test Device Lawn Mower"

    def _make_location(self, device):
        """Create a mock location containing the device."""
        location = Mock()
        location.devices = {device.id: device}
        return location

    def test_entity_available_when_coordinator_successful(self, mock_coordinator, mock_device):
        """Test entity availability when coordinator is successful."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None
        mock_device.services = {"MOWER": [Mock()]}
        mock_coordinator.locations = {"loc1": self._make_location(mock_device)}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is True

    def test_entity_unavailable_when_coordinator_failed(self, mock_coordinator, mock_device):
        """Test entity availability when coordinator failed."""
        mock_coordinator.last_update_success = False
        mock_coordinator.websocket_client = None
        mock_coordinator.locations = {}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is False

    def test_entity_unavailable_when_device_not_found(self, mock_coordinator, mock_device):
        """Test entity availability when device not found."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None
        mock_coordinator.locations = {"loc1": Mock(devices={})}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is False

    def test_entity_unavailable_when_service_not_found(self, mock_coordinator, mock_device):
        """Test entity availability when service not found."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None
        mock_device.services = {}
        mock_coordinator.locations = {"loc1": self._make_location(mock_device)}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is True  # No COMMON service => assume available

    def test_entity_unavailable_when_rf_offline(self, mock_coordinator, mock_device):
        """Test entity availability when RF link is offline."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None

        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = "OFFLINE"
        mock_device.services = {"COMMON": [common_service], "MOWER": [Mock()]}
        mock_coordinator.locations = {"loc1": self._make_location(mock_device)}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is False

    def test_entity_available_when_rf_online(self, mock_coordinator, mock_device):
        """Test entity availability when RF link is online."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None

        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = "ONLINE"
        mock_device.services = {"COMMON": [common_service], "MOWER": [Mock()]}
        mock_coordinator.locations = {"loc1": self._make_location(mock_device)}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is True

    def test_entity_available_when_no_rf_state(self, mock_coordinator, mock_device):
        """Test entity availability when no RF link state."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None

        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = None
        mock_device.services = {"COMMON": [common_service], "MOWER": [Mock()]}
        mock_coordinator.locations = {"loc1": self._make_location(mock_device)}

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        assert entity.available is True

    def test_entity_extra_state_attributes(self, mock_coordinator, mock_device):
        """Test entity extra state attributes."""
        mock_coordinator.last_update_success = True
        mock_coordinator.websocket_client = None

        common_service = Mock(spec=GardenaCommonService)
        common_service.battery_level = 80
        common_service.battery_state = "OK"
        common_service.rf_link_level = 100
        common_service.rf_link_state = "ONLINE"

        mock_device.services = {
            "COMMON": [common_service],
            "MOWER": [Mock()]
        }

        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")
        attrs = entity.extra_state_attributes

        assert attrs["battery_level"] == 80
        assert attrs["battery_state"] == "OK"
        assert attrs["rf_link_level"] == 100
        assert attrs["rf_link_state"] == "ONLINE"

    def test_service_display_names(self, mock_coordinator, mock_device):
        """Test service display names."""
        mock_coordinator.websocket_client = None
        entity = GardenaEntity(mock_coordinator, mock_device, "MOWER")

        test_cases = [
            ("COMMON", "Status"),
            ("MOWER", "Lawn Mower"),
            ("POWER_SOCKET", "Power Socket"),
            ("VALVE", "Valve"),
            ("VALVE_SET", "Valve Set"),
            ("SENSOR", "Sensor"),
            ("UNKNOWN", "Unknown"),
        ]

        for service_type, expected_name in test_cases:
            entity.service_type = service_type
            assert entity._get_service_display_name() == expected_name


class TestGardenaBatteryEntity:
    """Test GardenaBatteryEntity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_device(self):
        """Create a mock device."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        device.name = "Test Device"
        device.model_type = "Test Model"
        device.serial = "12345"
        device.location_id = "test-location-1"
        device.services = {}
        return device

    def test_battery_entity_initialization(self, mock_coordinator, mock_device):
        """Test battery entity initialization."""
        mock_coordinator.websocket_client = None
        entity = GardenaBatteryEntity(mock_coordinator, mock_device)

        assert entity._attr_unique_id == "test-device-1_COMMON"

    def test_battery_value_with_level(self, mock_coordinator, mock_device):
        """Test battery value when level is available."""
        mock_coordinator.websocket_client = None
        common_service = Mock(spec=GardenaCommonService)
        common_service.battery_level = 75
        mock_device.services = {"COMMON": [common_service]}

        entity = GardenaBatteryEntity(mock_coordinator, mock_device)

        assert entity.battery_level == 75

    def test_battery_value_without_level(self, mock_coordinator, mock_device):
        """Test battery value when level is not available."""
        mock_coordinator.websocket_client = None
        common_service = Mock(spec=GardenaCommonService)
        common_service.battery_level = None
        mock_device.services = {"COMMON": [common_service]}

        entity = GardenaBatteryEntity(mock_coordinator, mock_device)

        assert entity.battery_level is None

    def test_battery_value_without_common_service(self, mock_coordinator, mock_device):
        """Test battery value when common service is not available."""
        mock_coordinator.websocket_client = None
        mock_device.services = {}

        entity = GardenaBatteryEntity(mock_coordinator, mock_device)

        assert entity.battery_level is None


class TestGardenaBatterySensorIcon:
    """Battery sensors must not hardcode an icon (issue #386)."""

    def test_battery_sensor_has_no_hardcoded_icon(self):
        """device_class BATTERY already picks a level-based icon."""
        from .sensor import GardenaBatterySensor

        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.last_update_success = True
        coordinator.websocket_client = None
        coordinator.locations = {}

        device = Mock(spec=GardenaDevice)
        device.id = "device-1"
        device.name = "Mower"
        device.serial = "12345"
        device.services = {}

        common_service = Mock(spec=GardenaCommonService)
        common_service.id = "common-1"

        entity = GardenaBatterySensor(coordinator, device, common_service)
        assert getattr(entity, "_attr_icon", None) is None
        assert entity._attr_device_class is not None


class TestGardenaOnlineEntity:
    """Test GardenaOnlineEntity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.last_update_success = True
        return coordinator

    @pytest.fixture
    def mock_device(self):
        """Create a mock device."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        device.name = "Test Device"
        device.model_type = "Test Model"
        device.serial = "12345"
        device.location_id = "test-location-1"
        device.services = {}
        return device

    def test_online_entity_initialization(self, mock_coordinator, mock_device):
        """Test online entity initialization."""
        mock_coordinator.websocket_client = None
        entity = GardenaOnlineEntity(mock_coordinator, mock_device)

        assert entity._attr_unique_id == "test-device-1_COMMON"

    def test_online_status_when_online(self, mock_coordinator, mock_device):
        """Test online status when device is online."""
        mock_coordinator.websocket_client = None
        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = "ONLINE"
        mock_device.services = {"COMMON": [common_service]}
        mock_coordinator.get_device_by_id.return_value = mock_device

        entity = GardenaOnlineEntity(mock_coordinator, mock_device)

        assert entity.is_on is True

    def test_online_status_when_offline(self, mock_coordinator, mock_device):
        """Test online status when device is offline."""
        mock_coordinator.websocket_client = None
        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = "OFFLINE"
        mock_device.services = {"COMMON": [common_service]}
        mock_coordinator.get_device_by_id.return_value = mock_device

        entity = GardenaOnlineEntity(mock_coordinator, mock_device)

        assert entity.is_on is False

    def test_online_status_without_common_service(self, mock_coordinator, mock_device):
        """Test online status when common service is not available."""
        mock_coordinator.websocket_client = None
        mock_device.services = {}
        mock_coordinator.get_device_by_id.return_value = mock_device

        entity = GardenaOnlineEntity(mock_coordinator, mock_device)

        assert entity.is_on is False

    def test_online_status_without_rf_state(self, mock_coordinator, mock_device):
        """Test online status when RF link state is not available."""
        mock_coordinator.websocket_client = None
        common_service = Mock(spec=GardenaCommonService)
        common_service.rf_link_state = None
        mock_device.services = {"COMMON": [common_service]}
        mock_coordinator.get_device_by_id.return_value = mock_device

        entity = GardenaOnlineEntity(mock_coordinator, mock_device)

        assert entity.is_on is False 