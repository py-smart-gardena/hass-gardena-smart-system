"""Client for Gardena Smart System API."""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from .auth import GardenaAuthError, GardenaAuthenticationManager

_LOGGER = logging.getLogger(__name__)

# Constants
SMART_HOST = "https://api.smart.gardena.dev"
API_TIMEOUT = 30


class GardenaAPIError(Exception):
    """API error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code


class GardenaSmartSystemClient:
    """Client for Gardena Smart System API."""

    def __init__(self, client_id: str, client_secret: str, api_key: Optional[str] = None, dev_mode: bool = False) -> None:
        """Initialize the client."""
        self.auth_manager = GardenaAuthenticationManager(client_id, client_secret, api_key, dev_mode)
        self._dev_mode = dev_mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=API_TIMEOUT)
            # Handle SSL issues on macOS in development
            connector = None
            if hasattr(self, '_dev_mode') and self._dev_mode:
                import ssl
                connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make authenticated request to Gardena API."""
        async with self._request_lock:
            # Ensure we have a valid token
            await self.auth_manager.authenticate()
            
            session = await self._get_session()
            url = f"{SMART_HOST}/v2{endpoint}"
            headers = self.auth_manager.get_auth_headers()
            
            _LOGGER.debug(f"Making {method} request to {url}")
            
            try:
                if data:
                    json_data = json.dumps(data, ensure_ascii=False)
                    _LOGGER.debug(f"Request data: {json_data}")
                    async with session.request(method, url, data=json_data, headers=headers) as response:
                        return await self._handle_response(response, retry_count)
                else:
                    async with session.request(method, url, headers=headers) as response:
                        return await self._handle_response(response, retry_count)
                        
            except aiohttp.ClientError as e:
                _LOGGER.error(f"Network error during API request: {e}")
                raise GardenaAPIError(f"Network error: {e}")

    async def _handle_response(self, response: aiohttp.ClientResponse, retry_count: int) -> Dict[str, Any]:
        """Handle API response with error checking and retry logic."""
        response_text = await response.text()
        _LOGGER.debug(f"Response status: {response.status}, body: {response_text}")
        
        if response.status in (200, 201, 202):
            if response_text:
                return await response.json()
            return {}
        
        # Handle specific error codes
        if response.status == 401:
            _LOGGER.error("Authentication failed (401)")
            raise GardenaAuthError("Authentication failed")
        elif response.status == 403:
            _LOGGER.error("Access denied (403)")
            raise GardenaAPIError("Access denied - check API key and permissions", 403)
        elif response.status == 404:
            _LOGGER.error("Resource not found (404)")
            raise GardenaAPIError("Resource not found", 404)
        elif response.status in (500, 502):
            # Retry server errors with exponential backoff
            if retry_count < 3:
                delay = 2 ** retry_count
                _LOGGER.warning(f"Server error {response.status}, retrying in {delay}s (attempt {retry_count + 1}/3)")
                await asyncio.sleep(delay)
                return await self._make_request("GET", "/locations", retry_count=retry_count + 1)
            else:
                _LOGGER.error(f"Server error after {retry_count} retries: {response.status}")
                raise GardenaAPIError(f"Server error: {response.status}", response.status)
        
        # Handle other errors
        try:
            error_data = await response.json()
            error_msg = error_data.get("message", "Unknown error")
        except:
            error_msg = response_text or f"HTTP {response.status}"
        
        _LOGGER.error(f"API error {response.status}: {error_msg}")
        raise GardenaAPIError(f"API error: {error_msg}", response.status)

    async def get_locations(self) -> List[Dict[str, Any]]:
        """Get all locations."""
        _LOGGER.debug("Fetching locations")
        try:
            response = await self._make_request("GET", "/locations")
            locations = response.get("data", [])
            _LOGGER.debug(f"Found {len(locations)} locations")
            return locations
        except Exception as e:
            _LOGGER.error(f"Failed to fetch locations: {e}")
            raise

    async def get_location(self, location_id: str) -> Dict[str, Any]:
        """Get specific location with devices."""
        _LOGGER.debug(f"Fetching location {location_id}")
        try:
            response = await self._make_request("GET", f"/locations/{location_id}")
            _LOGGER.debug(f"Location {location_id} fetched successfully")
            return response
        except Exception as e:
            _LOGGER.error(f"Failed to fetch location {location_id}: {e}")
            raise

    async def send_command(self, service_id: str, command_data: Dict[str, Any]) -> None:
        """Send command to device service."""
        _LOGGER.debug(f"Sending command to service {service_id}: {command_data}")
        try:
            await self._make_request("PUT", f"/command/{service_id}", data=command_data)
            _LOGGER.debug(f"Command sent successfully to service {service_id}")
        except Exception as e:
            _LOGGER.error(f"Failed to send command to service {service_id}: {e}")
            raise

    async def close(self) -> None:
        """Close the client."""
        _LOGGER.debug("Closing Gardena Smart System client")
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        await self.auth_manager.close() 