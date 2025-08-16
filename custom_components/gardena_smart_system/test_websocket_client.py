from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .auth import GardenaAuthenticationManager
from .websocket_client import GardenaWebSocketClient


@pytest.mark.asyncio
async def test_get_websocket_url_calls_authenticate():
    auth_manager = GardenaAuthenticationManager(
        client_id="client", client_secret="secret", api_key="api"
    )
    ws_client = GardenaWebSocketClient(auth_manager, event_callback=lambda x: None)

    fake_session = MagicMock()
    fake_response = MagicMock()
    fake_response.status = 201
    fake_response.json = AsyncMock(
        return_value={"data": {"attributes": {"url": "wss://example"}}}
    )
    fake_session.post.return_value.__aenter__.return_value = fake_response

    with patch.object(
        auth_manager, "authenticate", AsyncMock()
    ) as mock_auth, patch.object(
        auth_manager, "_get_session", AsyncMock(return_value=fake_session)
    ):
        await ws_client._get_websocket_url()
        mock_auth.assert_called_once()
        assert ws_client.websocket_url == "wss://example"
