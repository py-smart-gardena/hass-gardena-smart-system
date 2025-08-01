"""Integration tests for Gardena WebSocket functionality."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .coordinator import GardenaSmartSystemCoordinator
from .websocket_client import GardenaWebSocketClient


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.async_create_task = asyncio.create_task
        return hass

    @pytest.fixture
    def mock_client(self):
        """Create a mock Gardena client."""
        client = AsyncMock()
        client.auth_manager = AsyncMock()
        client.auth_manager._dev_mode = True
        client.auth_manager.get_auth_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Authorization-Provider": "husqvarna",
            "X-Api-Key": "test-api-key",
        }
        return client

    @pytest.fixture
    def coordinator(self, mock_hass, mock_client):
        """Create a coordinator instance."""
        return GardenaSmartSystemCoordinator(mock_hass, mock_client)

    @pytest.mark.asyncio
    async def test_websocket_client_integration(self, coordinator):
        """Test WebSocket client integration with coordinator."""
        # Mock WebSocket URL response
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "url": "wss://test-websocket-url.com"
                }
            }
        }
        
        coordinator.client.auth_manager.session.post.return_value.__aenter__.return_value = mock_response
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        with patch("websockets.connect", return_value=mock_websocket):
            # Start WebSocket client
            await coordinator._start_websocket()
            
            # Verify WebSocket client was created
            assert coordinator.websocket_client is not None
            assert coordinator.websocket_client.is_connected is True

    @pytest.mark.asyncio
    async def test_service_update_processing(self, coordinator):
        """Test processing of service updates from WebSocket."""
        # Create a mock service update event
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
        
        # Mock device and service in coordinator
        from .models import GardenaDevice, GardenaValveService
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
        
        from .models import GardenaLocation
        mock_location = GardenaLocation(
            id="test-location",
            name="Test Location"
        )
        mock_location.devices = {"test-device-id": mock_device}
        coordinator.locations = {"test-location": mock_location}
        
        # Process the service update
        await coordinator._process_service_update(service_update_event)
        
        # Verify the service was updated
        updated_service = mock_device.services["VALVE"][0]
        assert updated_service.activity == "MANUAL_WATERING"
        assert updated_service.state == "OK"

    @pytest.mark.asyncio
    async def test_websocket_message_processing(self, coordinator):
        """Test processing of WebSocket messages."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        
        # Create a mock WebSocket message
        websocket_message = {
            "id": "test-service-id",
            "type": "VALVE",
            "relationships": {
                "device": {
                    "data": {
                        "id": "test-device-id",
                        "type": "DEVICE"
                    }
                }
            },
            "attributes": {
                "name": {"value": "Test Valve"},
                "activity": {"value": "MANUAL_WATERING"},
                "state": {"value": "OK"},
            }
        }
        
        # Mock the event callback
        event_callback = AsyncMock()
        coordinator.websocket_client.event_callback = event_callback
        
        # Process the message
        await coordinator.websocket_client._process_service_update(websocket_message)
        
        # Verify the callback was called with correct event
        event_callback.assert_called_once()
        call_args = event_callback.call_args[0][0]
        assert call_args["type"] == "service_update"
        assert call_args["service_id"] == "test-service-id"
        assert call_args["service_type"] == "VALVE"
        assert call_args["device_id"] == "test-device-id"

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self, coordinator):
        """Test WebSocket reconnection logic."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        coordinator.websocket_client.is_connected = False
        coordinator.websocket_client.reconnect_attempts = 0
        coordinator.websocket_client._shutdown = False
        
        # Mock reconnection
        with patch.object(coordinator.websocket_client, '_connect') as mock_connect:
            await coordinator.websocket_client._schedule_reconnect()
            
            # Verify reconnection was scheduled
            assert coordinator.websocket_client.reconnect_attempts == 1
            assert coordinator.websocket_client.reconnect_task is not None

    @pytest.mark.asyncio
    async def test_websocket_shutdown(self, coordinator):
        """Test WebSocket shutdown."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        coordinator.websocket_client.is_connected = True
        coordinator.websocket_client.websocket = AsyncMock()
        
        # Shutdown WebSocket
        await coordinator.websocket_client.stop()
        
        # Verify shutdown
        assert coordinator.websocket_client._shutdown is True
        assert coordinator.websocket_client.is_connected is False
        coordinator.websocket_client.websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinator_shutdown_with_websocket(self, coordinator):
        """Test coordinator shutdown with WebSocket."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        
        # Shutdown coordinator
        await coordinator.async_shutdown()
        
        # Verify WebSocket was stopped
        coordinator.websocket_client.stop.assert_called_once()
        assert coordinator.websocket_client is None

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, coordinator):
        """Test WebSocket ping/pong handling."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        coordinator.websocket_client.websocket = AsyncMock()
        coordinator.websocket_client.is_connected = True
        
        # Mock ping message
        ping_message = {
            "data": {
                "type": "WEBSOCKET_PING",
                "attributes": {}
            }
        }
        
        # Process ping message
        await coordinator.websocket_client._process_message(ping_message)
        
        # Verify pong was sent
        coordinator.websocket_client.websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_connection_status(self, coordinator):
        """Test WebSocket connection status."""
        # Mock WebSocket client
        coordinator.websocket_client = AsyncMock()
        
        # Test different statuses
        coordinator.websocket_client._shutdown = True
        assert coordinator.websocket_client.connection_status == "stopped"
        
        coordinator.websocket_client._shutdown = False
        coordinator.websocket_client.is_connected = True
        assert coordinator.websocket_client.connection_status == "connected"
        
        coordinator.websocket_client.is_connected = False
        coordinator.websocket_client.is_connecting = True
        assert coordinator.websocket_client.connection_status == "connecting"
        
        coordinator.websocket_client.is_connecting = False
        assert coordinator.websocket_client.connection_status == "disconnected" 