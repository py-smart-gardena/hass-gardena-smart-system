"""Tests for Gardena Smart System authentication."""
import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .auth import GardenaAuthError, GardenaAuthenticationManager
from .gardena_client import GardenaAPIError, GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)


class TestGardenaAuthError:
    """Test GardenaAuthError exception."""

    def test_init_basic(self):
        """Test GardenaAuthError initialization."""
        error = GardenaAuthError("Test error")
        assert str(error) == "Test error"

    def test_init_with_message(self):
        """Test GardenaAuthError initialization with message."""
        error = GardenaAuthError("Authentication failed")
        assert str(error) == "Authentication failed"


class TestGardenaAuthenticationManager:
    """Test GardenaAuthenticationManager."""

    @pytest.fixture
    def auth_manager(self):
        """Create authentication manager for testing."""
        return GardenaAuthenticationManager(
            client_id="test-client-id",
            client_secret="test-client-secret",
            api_key="test-api-key"
        )

    def test_init(self, auth_manager):
        """Test initialization."""
        assert auth_manager.client_id == "test-client-id"
        assert auth_manager.client_secret == "test-client-secret"
        assert auth_manager.api_key == "test-api-key"
        assert auth_manager._access_token is None
        assert auth_manager._refresh_token is None
        assert auth_manager._token_expires_at is None

    def test_is_token_valid_no_token(self, auth_manager):
        """Test token validation with no token."""
        assert auth_manager._is_token_valid() is False

    def test_is_token_valid_expired_token(self, auth_manager):
        """Test token validation with expired token."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = asyncio.get_event_loop().time() - 600  # 10 minutes ago
        assert auth_manager._is_token_valid() is False

    def test_is_token_valid_valid_token(self, auth_manager):
        """Test token validation with valid token."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = asyncio.get_event_loop().time() + 3600  # 1 hour from now
        assert auth_manager._is_token_valid() is True

    def test_get_auth_headers(self, auth_manager):
        """Test getting authentication headers."""
        auth_manager._access_token = "test-token"
        headers = auth_manager.get_auth_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Authorization-Provider"] == "husqvarna"
        assert headers["X-Api-Key"] == "test-client-id"
        assert headers["Content-Type"] == "application/vnd.api+json"

    def test_get_auth_headers_no_token(self, auth_manager):
        """Test getting authentication headers without token."""
        headers = auth_manager.get_auth_headers()
        assert "Authorization" not in headers
        assert headers["Authorization-Provider"] == "husqvarna"
        assert headers["X-Api-Key"] == "test-client-id"
        assert headers["Content-Type"] == "application/vnd.api+json"

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self, auth_manager):
        """Test authentication when valid token exists."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = asyncio.get_event_loop().time() + 3600  # 1 hour from now
        
        token = await auth_manager.authenticate()
        assert token == "test-token"

    @pytest.mark.asyncio
    async def test_authenticate_initial_auth_success(self, auth_manager):
        """Test successful initial authentication."""
        mock_response = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }

        with patch.object(auth_manager, '_get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            mock_response_obj.text = AsyncMock(return_value="{}")
            
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response_obj
            
            token = await auth_manager.authenticate()
            
            assert token == "new-access-token"
            assert auth_manager._access_token == "new-access-token"
            assert auth_manager._refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_authenticate_initial_auth_failure(self, auth_manager):
        """Test failed initial authentication."""
        with patch.object(auth_manager, '_get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            mock_response_obj = MagicMock()
            mock_response_obj.status = 401
            mock_response_obj.text = AsyncMock(return_value="Unauthorized")
            
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response_obj
            
            with pytest.raises(GardenaAuthError, match="Authentication failed: 401 - Unauthorized"):
                await auth_manager.authenticate()

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_manager):
        """Test successful token refresh."""
        auth_manager._refresh_token = "old-refresh-token"
        
        mock_response = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }

        with patch.object(auth_manager, '_get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            mock_response_obj.text = AsyncMock(return_value="{}")
            
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response_obj
            
            await auth_manager._refresh_access_token()
            
            assert auth_manager._access_token == "new-access-token"
            assert auth_manager._refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, auth_manager):
        """Test failed token refresh."""
        auth_manager._refresh_token = "old-refresh-token"
        
        with patch.object(auth_manager, '_get_session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            
            mock_response_obj = MagicMock()
            mock_response_obj.status = 401
            mock_response_obj.text = AsyncMock(return_value="Invalid refresh token")
            
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response_obj
            
            with pytest.raises(GardenaAuthError, match="Token refresh failed: 401 - Invalid refresh token"):
                await auth_manager._refresh_access_token()

    @pytest.mark.asyncio
    async def test_close(self, auth_manager):
        """Test closing the authentication manager."""
        # Create a mock session first
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        auth_manager._session = mock_session
        
        await auth_manager.close()
        
        mock_session.close.assert_called_once()
        assert auth_manager._session is None


class TestGardenaSmartSystemClient:
    """Test GardenaSmartSystemClient."""

    @pytest.fixture
    def client(self):
        """Create client for testing."""
        return GardenaSmartSystemClient(
            client_id="test-client-id",
            client_secret="test-client-secret",
            api_key="test-api-key"
        )

    def test_init(self, client):
        """Test initialization."""
        assert client.auth_manager.client_id == "test-client-id"
        assert client.auth_manager.client_secret == "test-client-secret"
        assert client.auth_manager.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_locations_success(self, client):
        """Test successful locations fetch."""
        mock_locations = [
            {
                "id": "loc1", 
                "type": "LOCATION",
                "attributes": {
                    "name": "Location 1"
                }
            }
        ]
        mock_response = {"data": mock_locations}

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            locations = await client.get_locations()

            assert len(locations) == 1
            assert locations[0].id == "loc1"
            assert locations[0].name == "Location 1"

    @pytest.mark.asyncio
    async def test_get_locations_api_error(self, client):
        """Test locations fetch with API error."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("API Error", 500)

            with pytest.raises(GardenaAPIError, match="API Error"):
                await client.get_locations()

    @pytest.mark.asyncio
    async def test_get_location_success(self, client):
        """Test successful location fetch."""
        mock_location = {
            "data": {
                "id": "loc1",
                "type": "LOCATION", 
                "attributes": {
                    "name": "Location 1"
                },
                "relationships": {
                    "devices": {
                        "data": []
                    }
                }
            },
            "included": []
        }

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_location

            location = await client.get_location("loc1")

            assert location.id == "loc1"
            assert location.name == "Location 1"
            assert len(location.devices) == 0

    @pytest.mark.asyncio
    async def test_send_command_success(self, client):
        """Test successful command sending."""
        mock_response = {"status": "accepted", "message": "Command accepted for processing"}

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            command_data = {
                "id": "cmd_test",
                "type": "MOWER_CONTROL",
                "attributes": {
                    "command": "START_DONT_OVERRIDE"
                }
            }

            response = await client.send_command("test-service", command_data)

            assert response == mock_response
            mock_request.assert_called_once_with(
                "PUT", 
                "/command/test-service", 
                data=command_data,
                is_command=True
            )

    @pytest.mark.asyncio
    async def test_send_command_202_accepted(self, client):
        """Test command accepted with 202 status."""
        mock_response = {"status": "accepted", "message": "Command accepted for processing"}

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            command_data = {
                "id": "cmd_test",
                "type": "POWER_SOCKET_CONTROL",
                "attributes": {
                    "command": "START_SECONDS_TO_OVERRIDE",
                    "seconds": 3600
                }
            }

            response = await client.send_command("power-service", command_data)

            assert response["status"] == "accepted"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_400_error(self, client):
        """Test command with 400 error."""
        from .gardena_client import GardenaCommandError

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaCommandError("Invalid command parameters", 400)

            command_data = {
                "id": "cmd_test",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "INVALID_COMMAND"
                }
            }

            with pytest.raises(GardenaCommandError) as exc_info:
                await client.send_command("valve-service", command_data)

            assert exc_info.value.status_code == 400
            assert "Invalid command parameters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_403_error(self, client):
        """Test command with 403 error."""
        from .gardena_client import GardenaCommandError

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaCommandError("Command forbidden - check device permissions", 403)

            command_data = {
                "id": "cmd_test",
                "type": "MOWER_CONTROL",
                "attributes": {
                    "command": "START_DONT_OVERRIDE"
                }
            }

            with pytest.raises(GardenaCommandError) as exc_info:
                await client.send_command("mower-service", command_data)

            assert exc_info.value.status_code == 403
            assert "Command forbidden" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_409_conflict(self, client):
        """Test command with 409 conflict error."""
        from .gardena_client import GardenaCommandError

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaCommandError("Command conflict - device may be busy", 409)

            command_data = {
                "id": "cmd_test",
                "type": "POWER_SOCKET_CONTROL",
                "attributes": {
                    "command": "START_OVERRIDE"
                }
            }

            with pytest.raises(GardenaCommandError) as exc_info:
                await client.send_command("power-service", command_data)

            assert exc_info.value.status_code == 409
            assert "Command conflict" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_500_retry(self, client):
        """Test command with 500 error handling."""
        from .gardena_client import GardenaCommandError

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            # Mock a 500 error
            mock_request.side_effect = GardenaCommandError("Server error: 500", 500)

            command_data = {
                "id": "cmd_test",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "START_SECONDS_TO_OVERRIDE",
                    "seconds": 1800
                }
            }

            # This should raise the command error
            with pytest.raises(GardenaCommandError) as exc_info:
                await client.send_command("valve-service", command_data)

            assert exc_info.value.status_code == 500
            assert "Server error: 500" in str(exc_info.value)
            assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_send_command_500_max_retries(self, client):
        """Test command with 500 error exceeding max retries."""
        from .gardena_client import GardenaCommandError

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaCommandError("Server error: 500", 500)

            command_data = {
                "id": "cmd_test",
                "type": "MOWER_CONTROL",
                "attributes": {
                    "command": "PARK_UNTIL_NEXT_TASK"
                }
            }

            with pytest.raises(GardenaCommandError) as exc_info:
                await client.send_command("mower-service", command_data)

            assert exc_info.value.status_code == 500
            # Should have tried at least once
            assert mock_request.call_count >= 1

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the client."""
        with patch.object(client.auth_manager, 'close', new_callable=AsyncMock) as mock_auth_close:
            # Create a mock session first
            mock_session = MagicMock()
            mock_session.closed = False
            mock_session.close = AsyncMock()
            client._session = mock_session

            await client.close()

            mock_auth_close.assert_called_once()
            mock_session.close.assert_called_once()
            assert client._session is None


class TestAuthenticationErrorHandling:
    """Test authentication error handling."""

    @pytest.mark.asyncio
    async def test_401_unauthorized(self):
        """Test handling of 401 Unauthorized error."""
        client = GardenaSmartSystemClient("client_id", "client_secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAuthError("Authentication failed")
            
            with pytest.raises(GardenaAuthError):
                await client.get_locations()

    @pytest.mark.asyncio
    async def test_403_forbidden(self):
        """Test handling of 403 Forbidden error."""
        client = GardenaSmartSystemClient("client_id", "client_secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Access denied", 403)
            
            with pytest.raises(GardenaAPIError, match="Access denied"):
                await client.get_locations()

    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Test handling of 404 Not Found error."""
        client = GardenaSmartSystemClient("client_id", "client_secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Resource not found", 404)
            
            with pytest.raises(GardenaAPIError, match="Resource not found"):
                await client.get_locations()

    @pytest.mark.asyncio
    async def test_500_server_error(self):
        """Test handling of 500 Server Error."""
        client = GardenaSmartSystemClient("client_id", "client_secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Server error", 500)
            
            with pytest.raises(GardenaAPIError, match="Server error"):
                await client.get_locations()

    @pytest.mark.asyncio
    async def test_502_bad_gateway(self):
        """Test handling of 502 Bad Gateway error."""
        client = GardenaSmartSystemClient("client_id", "client_secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Bad gateway", 502)
            
            with pytest.raises(GardenaAPIError, match="Bad gateway"):
                await client.get_locations()


class TestConfigFlowAuthentication:
    """Test config flow authentication."""

    @pytest.mark.asyncio
    async def test_config_flow_success(self, hass):
        """Test successful config flow authentication."""
        from .config_flow import GardenaSmartSystemConfigFlow
        from . import config_flow

        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass

        # Create a mock client
        mock_client = MagicMock()
        mock_client.get_locations = AsyncMock(return_value=[{"id": "loc1", "name": "Test Location"}])
        mock_client.close = AsyncMock()

        # Replace the class in the module
        original_client = config_flow.GardenaSmartSystemClient
        config_flow.GardenaSmartSystemClient = MagicMock(return_value=mock_client)

        try:
            result = await flow.async_step_user({
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            })

            assert result["type"] == "create_entry"
            assert result["data"]["client_id"] == "test-client-id"
            assert result["data"]["client_secret"] == "test-client-secret"

            # Verify the client was created with correct parameters
            config_flow.GardenaSmartSystemClient.assert_called_once_with(
                client_id="test-client-id",
                client_secret="test-client-secret",
                dev_mode=False
            )

        finally:
            # Restore original class
            config_flow.GardenaSmartSystemClient = original_client

    @pytest.mark.asyncio
    async def test_config_flow_invalid_auth(self, hass):
        """Test config flow with invalid authentication."""
        from .config_flow import GardenaSmartSystemConfigFlow
        from .auth import GardenaAuthError
        from . import config_flow

        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass

        # Create a mock client
        mock_client = MagicMock()
        mock_client.get_locations = AsyncMock(side_effect=GardenaAuthError("Invalid credentials"))
        mock_client.close = AsyncMock()

        # Replace the class in the module
        original_client = config_flow.GardenaSmartSystemClient
        config_flow.GardenaSmartSystemClient = MagicMock(return_value=mock_client)

        try:
            result = await flow.async_step_user({
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            })

            assert result["type"] == "form"
            assert "errors" in result
            assert "base" in result["errors"]

        finally:
            # Restore original class
            config_flow.GardenaSmartSystemClient = original_client

    @pytest.mark.asyncio
    async def test_config_flow_no_locations(self, hass):
        """Test config flow with no locations found."""
        from .config_flow import GardenaSmartSystemConfigFlow
        from . import config_flow

        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass

        # Create a mock client
        mock_client = MagicMock()
        mock_client.get_locations = AsyncMock(return_value=[])
        mock_client.close = AsyncMock()

        # Replace the class in the module
        original_client = config_flow.GardenaSmartSystemClient
        config_flow.GardenaSmartSystemClient = MagicMock(return_value=mock_client)

        try:
            result = await flow.async_step_user({
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            })

            assert result["type"] == "form"
            assert "errors" in result
            assert "base" in result["errors"]

        finally:
            # Restore original class
            config_flow.GardenaSmartSystemClient = original_client 