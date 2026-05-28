"""Tests for Gardena WebSocket client."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

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
        auth_manager.get_auth_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Authorization-Provider": "husqvarna",
            "X-Api-Key": "test-api-key",
        }
        auth_manager.client_id = "test-api-key"
        auth_manager._dev_mode = False
        auth_manager._is_token_valid = lambda: True

        mock_session = AsyncMock()
        auth_manager._get_session = AsyncMock(return_value=mock_session)
        auth_manager._session = mock_session

        return auth_manager

    @pytest.fixture
    def mock_event_callback(self):
        """Create a mock event callback."""
        return AsyncMock()

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
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "data": {
                "attributes": {
                    "url": "wss://test-websocket-url.com"
                }
            }
        })

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_cm
        mock_auth_manager._get_session = AsyncMock(return_value=mock_session)

        websocket_client.coordinator = MagicMock()
        websocket_client.coordinator.locations = {"loc-1": MagicMock()}

        await websocket_client._get_websocket_url()

        assert websocket_client.websocket_url == "wss://test-websocket-url.com"

    @pytest.mark.asyncio
    async def test_get_websocket_url_failure(self, websocket_client, mock_auth_manager):
        """Test failed WebSocket URL retrieval."""
        mock_response = MagicMock()
        mock_response.status = 400

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_cm
        mock_auth_manager._get_session = AsyncMock(return_value=mock_session)

        websocket_client.coordinator = MagicMock()
        websocket_client.coordinator.locations = {"loc-1": MagicMock()}

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
        websocket_client.coordinator = MagicMock()
        websocket_client.coordinator.locations = {"loc-1": MagicMock()}

        mock_websocket = AsyncMock()

        with patch.object(websocket_client, '_get_websocket_url') as mock_get_url:
            async def set_url():
                websocket_client.websocket_url = "wss://test-websocket-url.com"
            mock_get_url.side_effect = set_url

            with patch.object(websocket_client, '_listen_for_messages', new_callable=AsyncMock):
                with patch("custom_components.gardena_smart_system.websocket_client.websockets.connect", new_callable=AsyncMock, return_value=mock_websocket):
                    await websocket_client._connect()

        assert websocket_client.is_connected is True
        assert websocket_client.is_connecting is False

        if websocket_client.listen_task and not websocket_client.listen_task.done():
            websocket_client.listen_task.cancel()
            try:
                await websocket_client.listen_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_connect_failure(self, websocket_client, mock_auth_manager):
        """Test failed WebSocket connection."""
        with patch.object(websocket_client, '_get_websocket_url') as mock_get_url:
            async def no_url():
                websocket_client.websocket_url = None
            mock_get_url.side_effect = no_url

            with patch.object(websocket_client, '_schedule_reconnect') as mock_reconnect:
                await websocket_client._connect()

        assert websocket_client.is_connected is False
        assert websocket_client.is_connecting is False
        mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_device_event(self, websocket_client, mock_event_callback):
        """Test processing device event."""
        event_data = {
            "attributes": {
                "device_id": "test-device-id",
                "service_id": "test-service-id",
                "service_type": "VALVE",
                "activity": "MANUAL_WATERING",
            }
        }

        await websocket_client._process_device_event(event_data)

        mock_event_callback.assert_called_once()
        call_args = mock_event_callback.call_args[0][0]
        assert call_args["type"] == "device_event"

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

        # Clean up task
        websocket_client.reconnect_task.cancel()
        try:
            await websocket_client.reconnect_task
        except asyncio.CancelledError:
            pass

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

        assert websocket_client.is_connected is True

    @pytest.mark.asyncio
    async def test_stop(self, websocket_client):
        """Test stopping WebSocket client."""
        mock_ws = AsyncMock()
        websocket_client.websocket = mock_ws
        websocket_client.is_connected = True

        mock_reconnect_task = MagicMock()
        mock_reconnect_task.done.return_value = False
        websocket_client.reconnect_task = mock_reconnect_task

        mock_listen_task = MagicMock()
        mock_listen_task.done.return_value = False
        websocket_client.listen_task = mock_listen_task

        await websocket_client.stop()

        assert websocket_client._shutdown is True
        assert websocket_client.is_connected is False
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_status(self, websocket_client):
        """Test connection status property."""
        websocket_client._shutdown = True
        assert websocket_client.connection_status == "stopped"

        websocket_client._shutdown = False
        websocket_client.is_connected = True
        assert websocket_client.connection_status == "connected"

        websocket_client.is_connected = False
        websocket_client.is_connecting = True
        assert websocket_client.connection_status == "connecting"

        websocket_client.is_connecting = False
        assert websocket_client.connection_status == "disconnected"

    @pytest.mark.asyncio
    async def test_listen_for_messages_device_event(self, websocket_client, mock_event_callback):
        """Test listening for device event messages."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        websocket_client._shutdown = False

        device_event_message = json.dumps({
            "type": "VALVE",
            "id": "test-service:1",
            "attributes": {
                "activity": {"value": "MANUAL_WATERING"}
            }
        })

        websocket_client.websocket.__aiter__.return_value = [device_event_message]

        with patch.object(websocket_client, '_process_message') as mock_process:
            with patch.object(websocket_client, '_schedule_reconnect'):
                await websocket_client._listen_for_messages()

        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_for_messages_ping(self, websocket_client):
        """Test listening for ping messages."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True

        ping_message = json.dumps({
            "data": {
                "type": "WEBSOCKET_PING",
                "attributes": {}
            }
        })

        websocket_client.websocket.__aiter__.return_value = [ping_message]

        with patch.object(websocket_client, '_send_pong') as mock_pong:
            with patch.object(websocket_client, '_schedule_reconnect'):
                await websocket_client._listen_for_messages()

        mock_pong.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_for_messages_connection_closed(self, websocket_client):
        """Test handling connection closed during message listening."""
        websocket_client.websocket = AsyncMock()
        websocket_client.is_connected = True
        websocket_client._shutdown = False

        websocket_client.websocket.__aiter__.side_effect = ConnectionClosed(None, None)

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

        websocket_client.websocket.__aiter__.side_effect = WebSocketException("Test error")

        with patch.object(websocket_client, '_schedule_reconnect') as mock_reconnect:
            await websocket_client._listen_for_messages()

        assert websocket_client.is_connected is False
        mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, websocket_client):
        """Test processing invalid JSON message."""
        await websocket_client._process_message("invalid json")

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, websocket_client):
        """Test processing message with unknown type."""
        unknown_message = {
            "data": {
                "type": "UNKNOWN_TYPE",
                "attributes": {}
            }
        }

        await websocket_client._process_message(unknown_message)
