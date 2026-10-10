"""Tests for Gardena Smart System services and commands."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, PropertyMock
from typing import Dict, Any

from .services import (
    GardenaCommand,
    MowerCommand,
    PowerSocketCommand,
    ValveCommand,
    GardenaServiceManager,
)
from .models import GardenaDevice, GardenaMowerService, GardenaPowerSocketService, GardenaValveService
from .coordinator import GardenaSmartSystemCoordinator


@pytest.fixture(autouse=True)
def mock_device_registry():
    """Mock the device registry for all tests."""
    with patch(
        "custom_components.gardena_smart_system.services.dr.async_get"
    ) as mock_dr:
        registry = Mock()
        registry.async_get.return_value = None
        mock_dr.return_value = registry
        yield mock_dr


class TestGardenaCommand:
    """Test GardenaCommand base class."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = GardenaCommand("test-service", "TEST_TYPE", param1="value1", param2="value2")
        
        assert command.service_id == "test-service"
        assert command.command_type == "TEST_TYPE"
        assert command.attributes["param1"] == "value1"
        assert command.attributes["param2"] == "value2"

    def test_command_to_dict(self):
        """Test command to_dict conversion."""
        command = GardenaCommand("test-service", "TEST_TYPE", param1="value1")
        result = command.to_dict()

        assert "data" in result
        assert result["data"]["id"] == "cmd_test-service_TEST_TYPE"
        assert result["data"]["type"] == "TEST_TYPE"
        assert result["data"]["attributes"]["param1"] == "value1"


class TestMowerCommand:
    """Test MowerCommand class."""

    def test_mower_command_initialization(self):
        """Test mower command initialization."""
        command = MowerCommand("mower-service", "START_SECONDS_TO_OVERRIDE", seconds=1800)
        
        assert command.service_id == "mower-service"
        assert command.command_type == "MOWER_CONTROL"
        assert command.attributes["command"] == "START_SECONDS_TO_OVERRIDE"
        assert command.attributes["seconds"] == 1800

    def test_mower_command_without_seconds(self):
        """Test mower command without seconds parameter."""
        command = MowerCommand("mower-service", "START_DONT_OVERRIDE")
        
        assert command.attributes["command"] == "START_DONT_OVERRIDE"
        assert "seconds" not in command.attributes

    def test_mower_command_to_dict(self):
        """Test mower command to_dict conversion."""
        command = MowerCommand("mower-service", "PARK_UNTIL_NEXT_TASK")
        result = command.to_dict()

        assert result["data"]["id"] == "cmd_mower-service_MOWER_CONTROL"
        assert result["data"]["type"] == "MOWER_CONTROL"
        assert result["data"]["attributes"]["command"] == "PARK_UNTIL_NEXT_TASK"

    def test_mower_commands_available(self):
        """Test that all mower commands are available."""
        expected_commands = {
            "START_SECONDS_TO_OVERRIDE",
            "START_DONT_OVERRIDE", 
            "PARK_UNTIL_NEXT_TASK",
            "PARK_UNTIL_FURTHER_NOTICE"
        }
        assert set(MowerCommand.COMMANDS.keys()) == expected_commands


class TestPowerSocketCommand:
    """Test PowerSocketCommand class."""

    def test_power_socket_command_initialization(self):
        """Test power socket command initialization."""
        command = PowerSocketCommand("power-service", "START_SECONDS_TO_OVERRIDE", seconds=3600)
        
        assert command.service_id == "power-service"
        assert command.command_type == "POWER_SOCKET_CONTROL"
        assert command.attributes["command"] == "START_SECONDS_TO_OVERRIDE"
        assert command.attributes["seconds"] == 3600

    def test_power_socket_command_indefinite(self):
        """Test power socket command for indefinite operation."""
        command = PowerSocketCommand("power-service", "START_OVERRIDE")
        
        assert command.attributes["command"] == "START_OVERRIDE"
        assert "seconds" not in command.attributes

    def test_power_socket_commands_available(self):
        """Test that all power socket commands are available."""
        expected_commands = {
            "START_SECONDS_TO_OVERRIDE",
            "START_OVERRIDE",
            "STOP_UNTIL_NEXT_TASK",
            "PAUSE",
            "UNPAUSE"
        }
        assert set(PowerSocketCommand.COMMANDS.keys()) == expected_commands


class TestValveCommand:
    """Test ValveCommand class."""

    def test_valve_command_initialization(self):
        """Test valve command initialization."""
        command = ValveCommand("valve-service", "START_SECONDS_TO_OVERRIDE", seconds=1800)
        
        assert command.service_id == "valve-service"
        assert command.command_type == "VALVE_CONTROL"
        assert command.attributes["command"] == "START_SECONDS_TO_OVERRIDE"
        assert command.attributes["seconds"] == 1800

    def test_valve_command_close(self):
        """Test valve close command."""
        command = ValveCommand("valve-service", "STOP_UNTIL_NEXT_TASK")
        
        assert command.attributes["command"] == "STOP_UNTIL_NEXT_TASK"
        assert "seconds" not in command.attributes

    def test_valve_pause_includes_seconds_when_duration_given(self):
        """PAUSE accepts an optional duration (#374)."""
        command = ValveCommand("valve-service", "PAUSE", seconds=3600)

        assert command.attributes["command"] == "PAUSE"
        assert command.attributes["seconds"] == 3600

    def test_valve_pause_omits_seconds_without_duration(self):
        """Omitting duration keeps the device's own pause length (#374)."""
        command = ValveCommand("valve-service", "PAUSE")

        assert command.attributes["command"] == "PAUSE"
        assert "seconds" not in command.attributes

    def test_valve_commands_available(self):
        """Test that all valve commands are available."""
        expected_commands = {
            "START_SECONDS_TO_OVERRIDE",
            "STOP_UNTIL_NEXT_TASK",
            "PAUSE",
            "UNPAUSE"
        }
        assert set(ValveCommand.COMMANDS.keys()) == expected_commands


class TestGardenaServiceManager:
    """Test GardenaServiceManager class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_register = Mock()  # Use regular Mock instead of AsyncMock
        return hass

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.client = Mock()
        coordinator.client.send_command = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_device(self):
        """Create a mock device with services."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        device.name = "Test Device"

        # Add mower service (as a list, matching real data structure)
        mower_service = Mock(spec=GardenaMowerService)
        mower_service.id = "mower-service-1"
        device.services = {"MOWER": [mower_service]}

        return device

    def test_service_manager_initialization(self, mock_hass):
        """Test service manager initialization."""
        service_manager = GardenaServiceManager(mock_hass)
        
        # Verify that services were registered
        assert mock_hass.services.async_register.call_count >= 12  # At least 12 services

    def test_get_coordinator_success(self, mock_hass, mock_coordinator, mock_device):
        """Test successful coordinator retrieval."""
        # Setup mock data
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = mock_device
        
        service_manager = GardenaServiceManager(mock_hass)
        result = service_manager._get_coordinator("test-device-1")
        
        assert result == mock_coordinator

    def test_get_coordinator_not_found(self, mock_hass):
        """Test coordinator retrieval when device not found."""
        mock_hass.data = {"gardena_smart_system": {}}
        
        service_manager = GardenaServiceManager(mock_hass)
        result = service_manager._get_coordinator("non-existent-device")
        
        assert result is None

    def test_get_device_service_id_success(self, mock_hass, mock_coordinator, mock_device):
        """Test successful service ID retrieval."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = mock_device
        
        service_manager = GardenaServiceManager(mock_hass)
        result = service_manager._get_device_service_id("test-device-1", "MOWER")
        
        assert result == "mower-service-1"

    def test_get_device_service_id_service_not_found(self, mock_hass, mock_coordinator, mock_device):
        """Test service ID retrieval when service not found."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = mock_device
        
        service_manager = GardenaServiceManager(mock_hass)
        result = service_manager._get_device_service_id("test-device-1", "NON_EXISTENT")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_send_command_success(self, mock_hass, mock_coordinator):
        """Test successful command sending."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}
        
        service_manager = GardenaServiceManager(mock_hass)
        command = MowerCommand("test-service", "START_DONT_OVERRIDE")
        
        result = await service_manager._send_command("test-service", command)
        
        assert result is True
        mock_coordinator.client.send_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_failure(self, mock_hass, mock_coordinator):
        """Test command sending failure."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.client.send_command.side_effect = Exception("Command failed")
        
        service_manager = GardenaServiceManager(mock_hass)
        command = MowerCommand("test-service", "START_DONT_OVERRIDE")

        from homeassistant.exceptions import HomeAssistantError

        with pytest.raises(HomeAssistantError, match="Command failed"):
            await service_manager._send_command("test-service", command)

    @pytest.mark.asyncio
    async def test_mower_start_service(self, mock_hass, mock_coordinator, mock_device):
        """Test mower start service."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = mock_device
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}
        
        service_manager = GardenaServiceManager(mock_hass)
        
        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1"}
        
        await service_manager._service_mower_start(mock_call)

        # Verify command was sent
        mock_coordinator.client.send_command.assert_called_once()
        call_args = mock_coordinator.client.send_command.call_args[0]
        assert call_args[0] == "mower-service-1"
        assert call_args[1]["data"]["attributes"]["command"] == "START_DONT_OVERRIDE"

    @pytest.mark.asyncio
    async def test_mower_start_manual_service(self, mock_hass, mock_coordinator, mock_device):
        """Test mower start manual service."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = mock_device
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}

        service_manager = GardenaServiceManager(mock_hass)

        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1", "duration": 1800}

        await service_manager._service_mower_start_manual(mock_call)

        # Verify command was sent
        mock_coordinator.client.send_command.assert_called_once()
        call_args = mock_coordinator.client.send_command.call_args[0]
        assert call_args[0] == "mower-service-1"
        assert call_args[1]["data"]["attributes"]["command"] == "START_SECONDS_TO_OVERRIDE"
        assert call_args[1]["data"]["attributes"]["seconds"] == 1800

    @pytest.mark.asyncio
    async def test_power_socket_on_service(self, mock_hass, mock_coordinator):
        """Test power socket on service."""
        # Setup device with power socket service (as a list)
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        power_service = Mock(spec=GardenaPowerSocketService)
        power_service.id = "power-service-1"
        device.services = {"POWER_SOCKET": [power_service]}
        
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = device
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}
        
        service_manager = GardenaServiceManager(mock_hass)
        
        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1", "duration": 3600}
        
        await service_manager._service_power_socket_on(mock_call)

        # Verify command was sent
        mock_coordinator.client.send_command.assert_called_once()
        call_args = mock_coordinator.client.send_command.call_args[0]
        assert call_args[0] == "power-service-1"
        assert call_args[1]["data"]["attributes"]["command"] == "START_SECONDS_TO_OVERRIDE"
        assert call_args[1]["data"]["attributes"]["seconds"] == 3600

    @pytest.mark.asyncio
    async def test_valve_open_service(self, mock_hass, mock_coordinator):
        """Test valve open service."""
        # Setup device with valve service (as a list)
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        valve_service = Mock(spec=GardenaValveService)
        valve_service.id = "valve-service-1"
        device.services = {"VALVE": [valve_service]}

        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = device
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}

        service_manager = GardenaServiceManager(mock_hass)

        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1", "duration": 1800}

        await service_manager._service_valve_open(mock_call)

        # Verify command was sent
        mock_coordinator.client.send_command.assert_called_once()
        call_args = mock_coordinator.client.send_command.call_args[0]
        assert call_args[0] == "valve-service-1"
        assert call_args[1]["data"]["attributes"]["command"] == "START_SECONDS_TO_OVERRIDE"
        assert call_args[1]["data"]["attributes"]["seconds"] == 1800

    @pytest.mark.asyncio
    async def test_valve_open_with_service_id(self, mock_hass, mock_coordinator):
        """Test valve open service with explicit service_id."""
        device = Mock(spec=GardenaDevice)
        device.id = "device-uuid"
        valve_service = Mock(spec=GardenaValveService)
        valve_service.id = "device-uuid:2"
        device.services = {"VALVE": [valve_service]}

        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = device
        mock_coordinator.client.send_command.return_value = {"status": "accepted"}

        service_manager = GardenaServiceManager(mock_hass)

        # Create mock service call with service_id directly
        mock_call = Mock()
        mock_call.data = {"service_id": "device-uuid:2", "duration": 1800}

        await service_manager._service_valve_open(mock_call)

        # Verify command was sent to the specified service_id
        mock_coordinator.client.send_command.assert_called_once()
        call_args = mock_coordinator.client.send_command.call_args[0]
        assert call_args[0] == "device-uuid:2"
        assert call_args[1]["data"]["attributes"]["command"] == "START_SECONDS_TO_OVERRIDE"

    @pytest.mark.asyncio
    async def test_valve_open_multi_valve_no_service_id(self, mock_hass, mock_coordinator):
        """Test valve open errors on multi-valve device without service_id."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        valve1 = Mock(spec=GardenaValveService)
        valve1.id = "test-device-1:1"
        valve2 = Mock(spec=GardenaValveService)
        valve2.id = "test-device-1:2"
        device.services = {"VALVE": [valve1, valve2]}

        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = device

        service_manager = GardenaServiceManager(mock_hass)

        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1", "duration": 1800}

        from homeassistant.exceptions import HomeAssistantError

        with pytest.raises(HomeAssistantError, match="service_id"):
            await service_manager._service_valve_open(mock_call)

        mock_coordinator.client.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_service_device_not_found(self, mock_hass, mock_coordinator):
        """Test service when device is not found."""
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = None
        
        service_manager = GardenaServiceManager(mock_hass)
        
        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "non-existent-device"}
        
        # This should not raise an exception, just log an error
        await service_manager._service_mower_start(mock_call)
        
        # Verify no command was sent
        mock_coordinator.client.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_service_service_not_found(self, mock_hass, mock_coordinator):
        """Test service when device service is not found."""
        device = Mock(spec=GardenaDevice)
        device.id = "test-device-1"
        device.services = {}  # No services
        
        mock_hass.data = {
            "gardena_smart_system": {
                "entry-1": mock_coordinator
            }
        }
        mock_coordinator.get_device_by_id.return_value = device
        
        service_manager = GardenaServiceManager(mock_hass)
        
        # Create mock service call
        mock_call = Mock()
        mock_call.data = {"device_id": "test-device-1"}
        
        # This should not raise an exception, just log an error
        await service_manager._service_mower_start(mock_call)
        
        # Verify no command was sent
        mock_coordinator.client.send_command.assert_not_called()


def _multi_valve_manager():
    """Service manager whose device exposes two VALVE services."""
    mock_hass = Mock()
    mock_hass.services = Mock()
    mock_hass.services.async_register = Mock()

    mock_coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    mock_coordinator.client = Mock()
    mock_coordinator.client.send_command = AsyncMock(return_value={"status": "accepted"})

    device = Mock(spec=GardenaDevice)
    device.id = "controller-1"
    valve1 = Mock(spec=GardenaValveService)
    valve1.id = "controller-1:1"
    valve2 = Mock(spec=GardenaValveService)
    valve2.id = "controller-1:2"
    device.services = {"VALVE": [valve1, valve2]}

    mock_hass.data = {"gardena_smart_system": {"entry-1": mock_coordinator}}
    mock_coordinator.get_device_by_id.return_value = device
    return GardenaServiceManager(mock_hass), mock_coordinator


class TestMultiValveCommands:
    """Device-level valve commands on a multi-valve controller (#396, #388)."""

    @pytest.mark.asyncio
    async def test_valve_pause_fans_out_to_every_valve(self):
        """Pausing a controller pauses every VALVE service, not none of them."""
        service_manager, mock_coordinator = _multi_valve_manager()
        mock_call = Mock()
        mock_call.data = {"device_id": "controller-1"}

        await service_manager._service_valve_pause(mock_call)

        sent = [
            call.args[0]
            for call in mock_coordinator.client.send_command.await_args_list
        ]
        commands = [
            call.args[1]["data"]["attributes"]["command"]
            for call in mock_coordinator.client.send_command.await_args_list
        ]
        assert sent == ["controller-1:1", "controller-1:2"]
        assert commands == ["PAUSE", "PAUSE"]
        for call in mock_coordinator.client.send_command.await_args_list:
            assert "seconds" not in call.args[1]["data"]["attributes"]

    @pytest.mark.asyncio
    async def test_valve_close_fans_out_to_every_valve(self):
        """Closing a controller closes every VALVE service (#396)."""
        service_manager, mock_coordinator = _multi_valve_manager()
        mock_call = Mock()
        mock_call.data = {"device_id": "controller-1"}

        await service_manager._service_valve_close(mock_call)

        sent = [
            call.args[0]
            for call in mock_coordinator.client.send_command.await_args_list
        ]
        commands = [
            call.args[1]["data"]["attributes"]["command"]
            for call in mock_coordinator.client.send_command.await_args_list
        ]
        assert sent == ["controller-1:1", "controller-1:2"]
        assert commands == ["STOP_UNTIL_NEXT_TASK", "STOP_UNTIL_NEXT_TASK"]

    @pytest.mark.asyncio
    async def test_valve_pause_service_id_targets_one_valve(self):
        """An explicit service_id still pauses only that valve."""
        service_manager, mock_coordinator = _multi_valve_manager()
        mock_call = Mock()
        mock_call.data = {"service_id": "controller-1:2", "duration": 7200}

        await service_manager._service_valve_pause(mock_call)

        mock_coordinator.client.send_command.assert_awaited_once()
        service_id, payload = mock_coordinator.client.send_command.await_args.args
        assert service_id == "controller-1:2"
        assert payload["data"]["attributes"]["command"] == "PAUSE"
        assert payload["data"]["attributes"]["seconds"] == 7200

    @pytest.mark.asyncio
    async def test_valve_pause_without_target_raises(self):
        """A pause that cannot find a valve fails the service call (#396)."""
        from homeassistant.exceptions import HomeAssistantError

        mock_hass = Mock()
        mock_hass.services = Mock()
        mock_hass.services.async_register = Mock()
        mock_coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        mock_coordinator.client = Mock()
        mock_coordinator.client.send_command = AsyncMock()
        mock_hass.data = {"gardena_smart_system": {"entry-1": mock_coordinator}}
        mock_coordinator.get_device_by_id.return_value = None
        service_manager = GardenaServiceManager(mock_hass)
        mock_call = Mock()
        mock_call.data = {"device_id": "missing"}

        with pytest.raises(HomeAssistantError):
            await service_manager._service_valve_pause(mock_call)

        mock_coordinator.client.send_command.assert_not_called()


def test_valve_pause_schema_duration_is_optional_multiple_of_60():
    """Pause duration is optional and must be a multiple of 60, max 4 hours (#374)."""
    import voluptuous as vol

    from .services import SERVICE_SCHEMA_VALVE_PAUSE

    without_duration = SERVICE_SCHEMA_VALVE_PAUSE({"device_id": "controller-1"})
    assert "duration" not in without_duration

    with_duration = SERVICE_SCHEMA_VALVE_PAUSE(
        {"service_id": "controller-1:1", "duration": 1800}
    )
    assert with_duration["duration"] == 1800

    with pytest.raises(vol.Invalid):
        SERVICE_SCHEMA_VALVE_PAUSE({"device_id": "controller-1", "duration": 90})
    with pytest.raises(vol.Invalid):
        SERVICE_SCHEMA_VALVE_PAUSE({"device_id": "controller-1", "duration": 14401})


def test_mower_schema_allows_24_hour_duration():
    """Manual mower duration matches the power-socket 24h cap (issue #385)."""
    import voluptuous as vol

    from .services import SERVICE_SCHEMA_MOWER

    SERVICE_SCHEMA_MOWER({"device_id": "mower-1", "duration": 86400})
    with pytest.raises(vol.Invalid):
        SERVICE_SCHEMA_MOWER({"device_id": "mower-1", "duration": 86401}) 