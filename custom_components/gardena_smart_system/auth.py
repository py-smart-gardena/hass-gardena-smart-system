"""Authentication management for Gardena Smart System API."""
import asyncio
import logging
import ssl
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout

_LOGGER = logging.getLogger(__name__)

# Constants
AUTH_HOST = "https://api.authentication.husqvarnagroup.dev"
SMART_HOST = "https://api.smart.gardena.dev"
API_TIMEOUT = 30


class GardenaAuthError(Exception):
    """Authentication error."""

    pass


class GardenaAuthenticationManager:
    """Manages authentication for Gardena Smart System API."""

    def __init__(self, client_id: str, client_secret: str, api_key: Optional[str] = None, dev_mode: bool = False):
        """Initialize the authentication manager."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self._dev_mode = dev_mode
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._auth_lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=API_TIMEOUT)
            # Handle SSL issues on macOS in development
            connector = None
            if self._dev_mode:
                import ssl
                connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session

    def _is_token_valid(self) -> bool:
        """Check if current token is valid."""
        if not self._access_token:
            return False
        if not self._token_expires_at:
            return False
        # Token expires 10 minutes before actual expiry to be safe and prevent interruptions
        return asyncio.get_event_loop().time() < (self._token_expires_at - 600)

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise GardenaAuthError("No refresh token available")

        _LOGGER.debug("Refreshing access token")
        session = await self._get_session()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            async with session.post(
                f"{AUTH_HOST}/v1/oauth2/token",
                data=data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get("access_token")
                    self._refresh_token = token_data.get("refresh_token", self._refresh_token)
                    expires_in = token_data.get("expires_in", 3600)
                    self._token_expires_at = asyncio.get_event_loop().time() + expires_in
                    _LOGGER.debug("Access token refreshed successfully")
                else:
                    error_text = await response.text()
                    _LOGGER.error(f"Failed to refresh token: {response.status} - {error_text}")
                    # Invalidate tokens on refresh failure
                    self._access_token = None
                    self._refresh_token = None
                    self._token_expires_at = None
                    raise GardenaAuthError(f"Token refresh failed: {response.status} - {error_text}")
        except aiohttp.ClientError as e:
            raise GardenaAuthError(f"Network error during token refresh: {e}")

    async def authenticate(self) -> str:
        """Authenticate and return access token."""
        async with self._auth_lock:
            # Check if we have a valid token
            if self._is_token_valid():
                _LOGGER.debug("Using existing valid access token")
                return self._access_token

            # Perform new authentication
            _LOGGER.debug("Performing new authentication")
            session = await self._get_session()

            # Use client credentials flow
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            _LOGGER.info("Performing initial authentication with client credentials")
            _LOGGER.debug(f"Making auth request to {AUTH_HOST}/v1/oauth2/token with headers: {headers}")

            try:
                async with session.post(
                    f"{AUTH_HOST}/v1/oauth2/token",
                    data=data,
                    headers=headers,
                ) as response:
                    _LOGGER.debug(f"Auth response status: {response.status}, body: {await response.text()}")
                    
                    if response.status == 200:
                        token_data = await response.json()
                        self._access_token = token_data.get("access_token")
                        self._refresh_token = token_data.get("refresh_token")
                        expires_in = token_data.get("expires_in", 3600)
                        self._token_expires_at = asyncio.get_event_loop().time() + expires_in
                        _LOGGER.info("Authentication successful")
                        return self._access_token
                    else:
                        error_text = await response.text()
                        _LOGGER.error(f"Authentication failed: {response.status} - {error_text}")
                        raise GardenaAuthError(f"Authentication failed: {response.status} - {error_text}")
            except aiohttp.ClientError as e:
                _LOGGER.error(f"Network error during authentication: {e}")
                raise GardenaAuthError(f"Network error during authentication: {e}")

    def get_auth_headers(self) -> dict:
        """Get authentication headers for API requests."""
        headers = {
            "Authorization-Provider": "husqvarna",
            "X-Api-Key": self.client_id,
            "Content-Type": "application/vnd.api+json",
        }
        
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return headers

    async def close(self) -> None:
        """Close the authentication manager."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
