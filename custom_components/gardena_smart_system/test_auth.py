"""Tests for Gardena Smart System authentication."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from .auth import GardenaAuthError, GardenaAuthenticationManager
from .gardena_client import GardenaAPIError, GardenaSmartSystemClient


class TestGardenaAuthError:
    """Test GardenaAuthError exception."""
    
    def test_init_with_status_code(self):
        """Test GardenaAuthError initialization with status code."""
        error = GardenaAuthError("Test error", status_code=401)
        assert str(error) == "Test error"
        assert error.status_code == 401
        assert error.response_data is None
    
    def test_init_with_response_data(self):
        """Test GardenaAuthError initialization with response data."""
        response_data = {"error": "invalid_client"}
        error = GardenaAuthError("Test error", status_code=400, response_data=response_data)
        assert error.status_code == 400
        assert error.response_data == response_data


class TestGardenaAuthenticationManager:
    """Test GardenaAuthenticationManager."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a test authentication manager."""
        return GardenaAuthenticationManager(
            client_id="test-client-id",
            client_secret="test-client-secret",
            api_key="test-api-key"
        )
    
    def test_init(self, auth_manager):
        """Test authentication manager initialization."""
        assert auth_manager.client_id == "test-client-id"
        assert auth_manager.client_secret == "test-client-secret"
        assert auth_manager.api_key == "test-api-key"
        assert auth_manager._access_token is None
        assert auth_manager._refresh_token is None
        assert auth_manager._token_expires_at is None
    
    def test_is_token_valid_no_token(self, auth_manager):
        """Test token validation when no token exists."""
        assert auth_manager._is_token_valid() is False
    
    def test_is_token_valid_expired_token(self, auth_manager):
        """Test token validation with expired token."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = datetime.now() - timedelta(minutes=10)
        assert auth_manager._is_token_valid() is False
    
    def test_is_token_valid_valid_token(self, auth_manager):
        """Test token validation with valid token."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = datetime.now() + timedelta(hours=1)
        assert auth_manager._is_token_valid() is True
    
    def test_get_auth_headers(self, auth_manager):
        """Test getting authentication headers."""
        auth_manager._access_token = "test-token"
        headers = auth_manager.get_auth_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/vnd.api+json"
        assert headers["X-Api-Key"] == "test-api-key"
    
    def test_get_auth_headers_no_api_key(self):
        """Test getting authentication headers without API key."""
        auth_manager = GardenaAuthenticationManager(
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        auth_manager._access_token = "test-token"
        headers = auth_manager.get_auth_headers()
        assert "X-Api-Key" not in headers
    
    def test_clear_tokens(self, auth_manager):
        """Test clearing tokens."""
        auth_manager._access_token = "test-token"
        auth_manager._refresh_token = "test-refresh"
        auth_manager._token_expires_at = datetime.now()
        
        auth_manager.clear_tokens()
        
        assert auth_manager._access_token is None
        assert auth_manager._refresh_token is None
        assert auth_manager._token_expires_at is None
    
    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self, auth_manager):
        """Test authentication when valid token exists."""
        auth_manager._access_token = "test-token"
        auth_manager._token_expires_at = datetime.now() + timedelta(hours=1)
        
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
        
        with patch.object(auth_manager, '_make_auth_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            token = await auth_manager.authenticate()
            
            assert token == "new-access-token"
            assert auth_manager._access_token == "new-access-token"
            assert auth_manager._refresh_token == "new-refresh-token"
            assert auth_manager._token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_authenticate_initial_auth_failure(self, auth_manager):
        """Test failed initial authentication."""
        with patch.object(auth_manager, '_make_auth_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAuthError("Auth failed", status_code=401)
            
            with pytest.raises(GardenaAuthError) as exc_info:
                await auth_manager.authenticate()
            
            assert "Auth failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_refresh_token_success(self, auth_manager):
        """Test successful token refresh."""
        auth_manager._refresh_token = "old-refresh-token"
        auth_manager._token_expires_at = datetime.now() - timedelta(minutes=10)
        
        mock_response = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }
        
        with patch.object(auth_manager, '_refresh_access_token', new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = None
            
            with patch.object(auth_manager, '_is_token_valid', return_value=True):
                token = await auth_manager.authenticate()
                
                assert token == "new-access-token"
                mock_refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_refresh_token_failure(self, auth_manager):
        """Test failed token refresh."""
        auth_manager._refresh_token = "old-refresh-token"
        auth_manager._token_expires_at = datetime.now() - timedelta(minutes=10)
        
        with patch.object(auth_manager, '_refresh_access_token', new_callable=AsyncMock) as mock_refresh:
            mock_refresh.side_effect = GardenaAuthError("Refresh failed", status_code=401)
            
            with patch.object(auth_manager, '_perform_initial_auth', new_callable=AsyncMock) as mock_initial:
                mock_initial.return_value = None
                
                with patch.object(auth_manager, '_is_token_valid', return_value=True):
                    await auth_manager.authenticate()
                    
                    # Should clear refresh token and fall back to initial auth
                    assert auth_manager._refresh_token is None
                    mock_initial.assert_called_once()


class TestGardenaSmartSystemClient:
    """Test GardenaSmartSystemClient."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return GardenaSmartSystemClient(
            client_id="test-client-id",
            client_secret="test-client-secret",
            api_key="test-api-key"
        )
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.auth_manager.client_id == "test-client-id"
        assert client.auth_manager.client_secret == "test-client-secret"
        assert client.auth_manager.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_get_locations_success(self, client):
        """Test successful locations fetch."""
        mock_locations = [{"id": "loc1", "name": "Location 1"}]
        mock_response = {"data": mock_locations}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            locations = await client.get_locations()
            
            assert locations == mock_locations
            mock_request.assert_called_once_with("GET", "/locations")
    
    @pytest.mark.asyncio
    async def test_get_locations_api_error(self, client):
        """Test locations fetch with API error."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("API Error", status_code=500)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_location_success(self, client):
        """Test successful location fetch."""
        mock_location = {"id": "loc1", "name": "Location 1"}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_location
            
            location = await client.get_location("loc1")
            
            assert location == mock_location
            mock_request.assert_called_once_with("GET", "/locations/loc1")
    
    @pytest.mark.asyncio
    async def test_send_command_success(self, client):
        """Test successful command sending."""
        command_data = {"command": "START", "duration": 3600}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}
            
            await client.send_command("service1", command_data)
            
            mock_request.assert_called_once_with(
                "PUT",
                "/command/service1",
                json={"data": command_data}
            )
    
    @pytest.mark.asyncio
    async def test_create_websocket_url_success(self, client):
        """Test successful WebSocket URL creation."""
        mock_websocket = {"url": "wss://test.com"}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_websocket
            
            websocket = await client.create_websocket_url("loc1")
            
            assert websocket == mock_websocket
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup."""
        with patch.object(client.auth_manager, 'close', new_callable=AsyncMock) as mock_auth_close:
            await client.close()
            mock_auth_close.assert_called_once()


class TestAuthenticationErrorHandling:
    """Test authentication error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_401_unauthorized(self):
        """Test handling of 401 Unauthorized error."""
        client = GardenaSmartSystemClient("test-id", "test-secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Unauthorized", status_code=401)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_403_forbidden(self):
        """Test handling of 403 Forbidden error."""
        client = GardenaSmartSystemClient("test-id", "test-secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Forbidden", status_code=403)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Test handling of 404 Not Found error."""
        client = GardenaSmartSystemClient("test-id", "test-secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Not Found", status_code=404)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_500_server_error(self):
        """Test handling of 500 Server Error."""
        client = GardenaSmartSystemClient("test-id", "test-secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Server Error", status_code=500)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_502_bad_gateway(self):
        """Test handling of 502 Bad Gateway error."""
        client = GardenaSmartSystemClient("test-id", "test-secret")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GardenaAPIError("Bad Gateway", status_code=502)
            
            with pytest.raises(GardenaAPIError) as exc_info:
                await client.get_locations()
            
            assert exc_info.value.status_code == 502


class TestConfigFlowAuthentication:
    """Test authentication in config flow."""
    
    @pytest.mark.asyncio
    async def test_config_flow_success(self, hass):
        """Test successful config flow authentication."""
        from .config_flow import GardenaSmartSystemConfigFlow
        
        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass
        
        with patch('custom_components.gardena_smart_system.config_flow.GardenaSmartSystemClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_locations.return_value = [{"id": "loc1", "name": "Test Location"}]
            mock_client.close = AsyncMock()
            
            result = await flow.async_step_user({
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            })
            
            assert result["type"] == "create_entry"
            assert result["data"]["client_id"] == "test-client-id"
            assert result["data"]["client_secret"] == "test-client-secret"
    
    @pytest.mark.asyncio
    async def test_config_flow_invalid_auth(self, hass):
        """Test config flow with invalid authentication."""
        from .config_flow import GardenaSmartSystemConfigFlow
        from .auth import GardenaAuthError
        
        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass
        
        with patch('custom_components.gardena_smart_system.config_flow.GardenaSmartSystemClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_locations.side_effect = GardenaAuthError("Invalid credentials", status_code=401)
            mock_client.close = AsyncMock()
            
            result = await flow.async_step_user({
                "client_id": "invalid-id",
                "client_secret": "invalid-secret"
            })
            
            assert result["type"] == "form"
            assert result["errors"]["base"] == "invalid_auth"
    
    @pytest.mark.asyncio
    async def test_config_flow_no_locations(self, hass):
        """Test config flow when no locations are found."""
        from .config_flow import GardenaSmartSystemConfigFlow
        
        flow = GardenaSmartSystemConfigFlow()
        flow.hass = hass
        
        with patch('custom_components.gardena_smart_system.config_flow.GardenaSmartSystemClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_locations.return_value = []
            mock_client.close = AsyncMock()
            
            result = await flow.async_step_user({
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            })
            
            assert result["type"] == "form"
            assert result["errors"]["base"] == "no_locations" 