"""Tests for Gardena WebSocket client."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .websocket_client import GardenaWebSocketClient


class TestGardenaWebSocketClient:
    """Test cases for GardenaWebSocketClient."""

    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock auth manager."""
        auth_manager = AsyncMock()
        auth_manager.get_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Authorization-Provider": "husqvarna",
            "X-Api-Key": "test-api-key",
        }
        auth_manager.api_key = "test-api-key"
        auth_manager.session = AsyncMock()
        return auth_manager

    @pytest.fixture
    def mock_event_callback(self):
        """Create a mock event callback."""
        return MagicMock()

    @pytest.fixture
    def websocket_client(self, mock_auth_manager, mock_event_callback):
        """Create a WebSocket client instance."""
        return GardenaWebSocketClient(
            auth_manager=mock_auth_manager,
            event_callback=mock_event_callback,
        )

    @pytest.mark.asyncio
    async def test_initialization(self, websocket_client):
        """Test WebSocket client initialization."""
        assert websocket_client.is_connected is False
        assert websocket_client.is_connecting is False
        assert websocket_client.websocket is None
        assert websocket_client.websocket_url is None
        assert websocket_client.connection_status == "disconnected"

    @pytest.mark.asyncio
    async def test_get_websocket_url_success(self, websocket_client, mock_auth_manager):
        """Test successful WebSocket URL retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "url": "wss://test-websocket-url.com"
                }
            }
        }
        
        mock_auth_manager.session.post.return_value.__aenter__.return_value = mock_response
        
        await websocket_client._get_websocket_url()
        
        assert websocket_client.websocket_url == "wss://test-websocket-url.com"
        mock_auth_manager.session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_websocket_url_failure(self, websocket_client, mock_auth_manager):
        """Test failed WebSocket URL retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 400
        
        mock_auth_manager.session.post.return_value.__aenter__.return_value = mock_response
        
        await websocket_client._get_websocket_url()
        
        assert websocket_client.websocket_url is None

    @pytest.mark.asyncio
    async def test_get_websocket_headers(self, websocket_client):
        """Test WebSocket headers generation."""
        headers = websocket_client._get_websocket_headers()
        
        assert headers["Authorization-Provider"] == "husqvarna"
        assert headers["X-Api-Key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_connect_success(self, websocket_client, mock_auth_manager):
        """Test successful WebSocket connection."""
        # Mock WebSocket URL retrieval
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "url": "wss://test-websocket-url.com"
                }
            }
        }
        mock_auth_manager.session.post.return_value.__aenter__.return_value = mock_response
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        with patch("websockets.connect", return_value=mock_websocket):
            await websocket_client._connect()
        
        assert websocket_client.is_connected is True
        assert websocket_client.is_connecting is False
        assert websocket_client.websocket is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self, websocket_client, mock_auth_manager):
        """Test failed WebSocket connection."""
        # Mock WebSocket URL retrieval failure
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_auth_manager.session.post.return_value.__aenter__.return_value = mock_response
        
        await websocket_client._connect()
        
        assert websocket_client.is_connected is False
        assert websocket_client.is_connecting is False
        assert websocket_client.reconnect_attempts == 1

    @pytest.mark.asyncio
    async def test_process_device_event(self, websocket_client, mock_event_callback):
        """Test processing device event."""
        event_data = {
            "device_id": "test-device-id",
            "service_id": "test-service-id",
            "service_type": "VALVE",
            "activity": "MANUAL_WATERING",
            "state": "OK",
        }
        
        await websocket_client._process_device_event(event_data)
        
        mock_event_callback.assert_called_once()
        call_args = mock_event_callback.call_args[0][0]
        assert call_args["type"] == "device_event"
        assert call_args["data"] == event_data

    @pytest.mark.asyncio
    async def test_send_pong(self, websocket_client):
        """Test sending pong response."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        
        await websocket_client._send_pong()
        
        websocket_client.websocket.send.assert_called_once()
        sent_data = json.loads(websocket_client.websocket.send.call_args[0][0])
        assert sent_data["data"]["type"] == "WEBSOCKET_PONG"

    @pytest.mark.asyncio
    async def test_schedule_reconnect(self, websocket_client):
        """Test scheduling reconnection."""
        websocket_client._shutdown = False
        websocket_client.reconnect_task = None
        
        await websocket_client._schedule_reconnect()
        
        assert websocket_client.reconnect_attempts == 1
        assert websocket_client.reconnect_task is not None

    @pytest.mark.asyncio
    async def test_schedule_reconnect_max_attempts(self, websocket_client):
        """Test max reconnection attempts."""
        websocket_client.reconnect_attempts = 10
        websocket_client._shutdown = False
        websocket_client.reconnect_task = None
        
        await websocket_client._schedule_reconnect()
        
        assert websocket_client.reconnect_task is None

    @pytest.mark.asyncio
    async def test_start_already_running(self, websocket_client):
        """Test starting when already running."""
        websocket_client.is_connected = True
        
        await websocket_client.start()
        
        # Should not start again
        assert websocket_client.is_connected is True

    @pytest.mark.asyncio
    async def test_stop(self, websocket_client):
        """Test stopping WebSocket client."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        websocket_client.reconnect_task = AsyncMock()
        websocket_client.listen_task = AsyncMock()
        
        await websocket_client.stop()
        
        assert websocket_client._shutdown is True
        assert websocket_client.is_connected is False
        websocket_client.websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_status(self, websocket_client):
        """Test connection status property."""
        # Test stopped
        websocket_client._shutdown = True
        assert websocket_client.connection_status == "stopped"
        
        # Test connected
        websocket_client._shutdown = False
        websocket_client.is_connected = True
        assert websocket_client.connection_status == "connected"
        
        # Test connecting
        websocket_client.is_connected = False
        websocket_client.is_connecting = True
        assert websocket_client.connection_status == "connecting"
        
        # Test disconnected
        websocket_client.is_connecting = False
        assert websocket_client.connection_status == "disconnected"

    @pytest.mark.asyncio
    async def test_listen_for_messages_device_event(self, websocket_client, mock_event_callback):
        """Test listening for device event messages."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        
        # Mock message
        device_event_message = {
            "data": {
                "type": "WEBSOCKET_EVENT",
                "attributes": {
                    "device_id": "test-device",
                    "service_id": "test-service",
                    "activity": "MANUAL_WATERING",
                }
            }
        }
        
        websocket_client.websocket.__aiter__.return_value = [json.dumps(device_event_message)]
        
        # Mock _process_message to avoid complex processing
        with patch.object(websocket_client, '_process_message') as mock_process:
            await websocket_client._listen_for_messages()
        
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_for_messages_ping(self, websocket_client):
        """Test listening for ping messages."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        
        # Mock ping message
        ping_message = {
            "data": {
                "type": "WEBSOCKET_PING",
                "attributes": {}
            }
        }
        
        websocket_client.websocket.__aiter__.return_value = [json.dumps(ping_message)]
        
        # Mock _send_pong to avoid actual sending
        with patch.object(websocket_client, '_send_pong') as mock_pong:
            await websocket_client._listen_for_messages()
        
        mock_pong.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_for_messages_connection_closed(self, websocket_client):
        """Test handling connection closed during message listening."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        websocket_client._shutdown = False
        
        # Mock connection closed exception
        websocket_client.websocket.__aiter__.side_effect = ConnectionClosed(1000, "Normal closure")
        
        # Mock _schedule_reconnect to avoid actual reconnection
        with patch.object(websocket_client, '_schedule_reconnect') as mock_reconnect:
            await websocket_client._listen_for_messages()
        
        assert websocket_client.is_connected is False
        mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_for_messages_websocket_exception(self, websocket_client):
        """Test handling WebSocket exception during message listening."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        websocket_client._shutdown = False
        
        # Mock WebSocket exception
        websocket_client.websocket.__aiter__.side_effect = WebSocketException("Test error")
        
        # Mock _schedule_reconnect to avoid actual reconnection
        with patch.object(websocket_client, '_schedule_reconnect') as mock_reconnect:
            await websocket_client._listen_for_messages()
        
        assert websocket_client.is_connected is False
        mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, websocket_client):
        """Test processing invalid JSON message."""
        invalid_message = "invalid json"
        
        # Should not raise exception
        await websocket_client._process_message(invalid_message)

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, websocket_client):
        """Test processing message with unknown type."""
        unknown_message = {
            "data": {
                "type": "UNKNOWN_TYPE",
                "attributes": {}
            }
        }
        
        # Should not raise exception
        await websocket_client._process_message(unknown_message) 