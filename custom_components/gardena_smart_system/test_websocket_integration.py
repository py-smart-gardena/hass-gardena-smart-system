"""Integration tests for Gardena WebSocket functionality."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice, GardenaLocation, GardenaValveService
from .websocket_client import GardenaWebSocketClient


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a coordinator instance with mocked parent."""
        with patch("homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__", return_value=None):
            coord = GardenaSmartSystemCoordinator.__new__(GardenaSmartSystemCoordinator)
            coord.client = AsyncMock()
            coord.locations = {}
            coord.websocket_client = None
            coord._initial_data_loaded = False
            coord.hass = MagicMock()
            coord.logger = MagicMock()
            coord.name = "gardena_smart_system"
            coord.last_update_success = True
            coord.async_set_updated_data = MagicMock()
            return coord

    @pytest.mark.asyncio
    async def test_websocket_client_integration(self, coordinator):
        """Test WebSocket client creation via coordinator."""
        coordinator.client.auth_manager = AsyncMock()
        coordinator.client.auth_manager._dev_mode = False

        with patch.object(GardenaWebSocketClient, 'start', new_callable=AsyncMock):
            await coordinator._start_websocket()

        assert coordinator.websocket_client is not None

    @pytest.mark.asyncio
    async def test_service_update_processing(self, coordinator):
        """Test processing of service updates from WebSocket."""
        service_update_event = {
            "type": "service_update",
            "service_id": "test-service-id",
            "service_type": "VALVE",
            "device_id": "test-device-id",
            "data": {
                "activity": {"value": "MANUAL_WATERING"},
                "state": {"value": "OK"},
            }
        }

        mock_device = GardenaDevice(
            id="test-device-id",
            name="Test Device",
            model_type="Test Model",
            serial="test-serial",
            services={"VALVE": [GardenaValveService(
                id="test-service-id",
                type="VALVE",
                device_id="test-device-id",
                name="Test Valve",
                state="CLOSED",
                activity="CLOSED",
                duration=None,
                last_error_code=None
            )]},
            location_id="test-location"
        )

        mock_location = GardenaLocation(id="test-location", name="Test Location")
        mock_location.devices = {"test-device-id": mock_device}
        coordinator.locations = {"test-location": mock_location}

        await coordinator._process_service_update(service_update_event)

        updated_service = mock_device.services["VALVE"][0]
        assert updated_service.activity == "MANUAL_WATERING"
        assert updated_service.state == "OK"

    @pytest.mark.asyncio
    async def test_service_update_with_duration(self, coordinator):
        """Test processing of service updates with duration timestamp."""
        service_update_event = {
            "type": "service_update",
            "service_id": "test-service-id",
            "service_type": "VALVE",
            "device_id": "test-device-id",
            "data": {
                "activity": {"value": "MANUAL_WATERING"},
                "state": {"value": "OK"},
                "duration": {"value": 1800, "timestamp": "2025-01-01T10:00:00Z"},
            }
        }

        mock_device = GardenaDevice(
            id="test-device-id",
            name="Test Device",
            model_type="Test Model",
            serial="test-serial",
            services={"VALVE": [GardenaValveService(
                id="test-service-id",
                type="VALVE",
                device_id="test-device-id",
                name="Test Valve",
                state="CLOSED",
                activity="CLOSED",
                duration=None,
                duration_timestamp=None,
                last_error_code=None
            )]},
            location_id="test-location"
        )

        mock_location = GardenaLocation(id="test-location", name="Test Location")
        mock_location.devices = {"test-device-id": mock_device}
        coordinator.locations = {"test-location": mock_location}

        await coordinator._process_service_update(service_update_event)

        updated_service = mock_device.services["VALVE"][0]
        assert updated_service.activity == "MANUAL_WATERING"
        assert updated_service.duration == 1800
        assert updated_service.duration_timestamp == "2025-01-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self, coordinator):
        """Test WebSocket reconnection logic."""
        ws_client = GardenaWebSocketClient(
            auth_manager=AsyncMock(),
            event_callback=AsyncMock(),
        )
        ws_client._shutdown = False
        ws_client.reconnect_task = None

        await ws_client._schedule_reconnect()

        assert ws_client.reconnect_attempts == 1
        assert ws_client.reconnect_task is not None

        ws_client.reconnect_task.cancel()
        try:
            await ws_client.reconnect_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_websocket_shutdown(self, coordinator):
        """Test WebSocket shutdown."""
        ws_client = GardenaWebSocketClient(
            auth_manager=AsyncMock(),
            event_callback=AsyncMock(),
        )
        ws_client.websocket = AsyncMock()
        ws_client.is_connected = True

        await ws_client.stop()

        assert ws_client._shutdown is True
        assert ws_client.is_connected is False

    @pytest.mark.asyncio
    async def test_coordinator_shutdown_with_websocket(self, coordinator):
        """Test coordinator shutdown with WebSocket."""
        mock_ws = AsyncMock()
        coordinator.websocket_client = mock_ws

        await coordinator.async_shutdown()

        mock_ws.stop.assert_called_once()
        assert coordinator.websocket_client is None

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, coordinator):
        """Test WebSocket ping/pong handling."""
        ws_client = GardenaWebSocketClient(
            auth_manager=AsyncMock(),
            event_callback=AsyncMock(),
        )
        ws_client.websocket = AsyncMock()
        ws_client.is_connected = True

        await ws_client._send_pong()

        ws_client.websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_connection_status(self, coordinator):
        """Test WebSocket connection status."""
        ws_client = GardenaWebSocketClient(
            auth_manager=AsyncMock(),
            event_callback=AsyncMock(),
        )

        ws_client._shutdown = True
        assert ws_client.connection_status == "stopped"

        ws_client._shutdown = False
        ws_client.is_connected = True
        assert ws_client.connection_status == "connected"

        ws_client.is_connected = False
        ws_client.is_connecting = True
        assert ws_client.connection_status == "connecting"

        ws_client.is_connecting = False
        assert ws_client.connection_status == "disconnected"

    @pytest.mark.asyncio
    async def test_initial_load_hits_rest_once(self, coordinator):
        """The first refresh must perform the REST load (locations + per location)."""
        coordinator.client.get_locations = AsyncMock(return_value=[
            GardenaLocation(id="loc-1", name="Garden", devices={})
        ])
        coordinator.client.get_location = AsyncMock(return_value=GardenaLocation(
            id="loc-1", name="Garden", devices={}
        ))

        assert coordinator._initial_data_loaded is False
        await coordinator._async_update_data()

        coordinator.client.get_locations.assert_awaited_once()
        coordinator.client.get_location.assert_awaited_once_with("loc-1")
        assert "loc-1" in coordinator.locations

    @pytest.mark.asyncio
    async def test_refresh_after_initial_load_makes_no_rest_call(self, coordinator):
        """Regression for #370.

        After the initial load, command-triggered refreshes must serve cached
        data without calling the REST API. Otherwise every valve open/close
        would silently cost a ``GET /locations`` + ``GET /locations/{id}`` and
        exhaust the 700 requests/week quota.
        """
        coordinator._initial_data_loaded = True
        coordinator.locations = {"loc-1": GardenaLocation(id="loc-1", name="Garden", devices={})}
        coordinator.client.get_locations = AsyncMock()
        coordinator.client.get_location = AsyncMock()

        result = await coordinator._async_update_data()

        coordinator.client.get_locations.assert_not_awaited()
        coordinator.client.get_location.assert_not_awaited()
        assert result == coordinator.locations
