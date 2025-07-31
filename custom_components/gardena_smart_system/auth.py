"""Authentication module for Gardena Smart System API."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientTimeout

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class GardenaAuthError(Exception):
    """Base exception for Gardena authentication errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class GardenaAuthenticationManager:
    """Manages authentication for Gardena Smart System API."""

    def __init__(self, client_id: str, client_secret: str, api_key: Optional[str] = None):
        """Initialize the authentication manager."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        
        # Token management
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_lock = asyncio.Lock()
        
        # Retry configuration
        self._max_retries = 3
        self._retry_delay = 1.0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=API_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _make_auth_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Gardena API."""
        session = await self._get_session()
        
        url = f"{API_BASE_URL}{endpoint}"
        request_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        
        if headers:
            request_headers.update(headers)
        
        if self.api_key:
            request_headers["X-Api-Key"] = self.api_key

        _LOGGER.debug("Making auth request to %s with headers: %s", url, request_headers)
        
        try:
            async with session.request(
                method, url, data=data, headers=request_headers
            ) as response:
                response_text = await response.text()
                _LOGGER.debug("Auth response status: %s, body: %s", response.status, response_text)
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = None
                    try:
                        error_data = await response.json()
                    except Exception:
                        pass
                    
                    raise GardenaAuthError(
                        f"Authentication request failed: {response.status} - {response_text}",
                        status_code=response.status,
                        response_data=error_data
                    )
                    
        except aiohttp.ClientError as e:
            _LOGGER.error("Network error during authentication: %s", e)
            raise GardenaAuthError(f"Network error during authentication: {e}") from e
        except Exception as e:
            _LOGGER.error("Unexpected error during authentication: %s", e)
            raise GardenaAuthError(f"Unexpected error during authentication: {e}") from e

    async def authenticate(self) -> str:
        """Authenticate and return access token."""
        async with self._auth_lock:
            # Check if we have a valid token
            if self._is_token_valid():
                _LOGGER.debug("Using existing valid access token")
                return self._access_token
            
            # Try to refresh token if available
            if self._refresh_token:
                try:
                    _LOGGER.debug("Attempting to refresh access token")
                    await self._refresh_access_token()
                    if self._is_token_valid():
                        return self._access_token
                except GardenaAuthError as e:
                    _LOGGER.warning("Token refresh failed: %s", e)
                    # Clear invalid refresh token
                    self._refresh_token = None
            
            # Perform new authentication
            _LOGGER.debug("Performing new authentication")
            await self._perform_initial_auth()
            return self._access_token

    async def _perform_initial_auth(self) -> None:
        """Perform initial authentication using client credentials."""
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        _LOGGER.info("Performing initial authentication with client credentials")
        
        try:
            response = await self._make_auth_request("POST", "/oauth2/token", data=auth_data)
            
            self._access_token = response.get("access_token")
            self._refresh_token = response.get("refresh_token")
            
            # Calculate token expiration
            expires_in = response.get("expires_in", 3600)  # Default 1 hour
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            if not self._access_token:
                raise GardenaAuthError("No access token received in response")
            
            _LOGGER.info("Authentication successful, token expires at %s", self._token_expires_at)
            
        except GardenaAuthError:
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error during initial authentication: %s", e)
            raise GardenaAuthError(f"Initial authentication failed: {e}") from e

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise GardenaAuthError("No refresh token available")
        
        auth_data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }
        
        _LOGGER.debug("Refreshing access token")
        
        try:
            response = await self._make_auth_request("POST", "/oauth2/token", data=auth_data)
            
            self._access_token = response.get("access_token")
            self._refresh_token = response.get("refresh_token", self._refresh_token)
            
            # Calculate new token expiration
            expires_in = response.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            if not self._access_token:
                raise GardenaAuthError("No access token received in refresh response")
            
            _LOGGER.debug("Token refresh successful, new token expires at %s", self._token_expires_at)
            
        except GardenaAuthError:
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error during token refresh: %s", e)
            raise GardenaAuthError(f"Token refresh failed: {e}") from e

    def _is_token_valid(self) -> bool:
        """Check if the current access token is valid."""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Add 5 minutes buffer to prevent token expiration during requests
        buffer_time = datetime.now() + timedelta(minutes=5)
        return self._token_expires_at > buffer_time

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/vnd.api+json",
        }
        
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        
        return headers

    async def close(self) -> None:
        """Close the authentication manager."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def clear_tokens(self) -> None:
        """Clear all stored tokens."""
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        _LOGGER.debug("All tokens cleared") 