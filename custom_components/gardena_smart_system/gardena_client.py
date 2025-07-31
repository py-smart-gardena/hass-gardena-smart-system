"""Client for Gardena Smart System API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from .auth import GardenaAuthError, GardenaAuthenticationManager
from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class GardenaAPIError(Exception):
    """Base exception for Gardena API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class GardenaSmartSystemClient:
    """Client for Gardena Smart System API."""

    def __init__(self, client_id: str, client_secret: str, api_key: Optional[str] = None) -> None:
        """Initialize the client."""
        self.auth_manager = GardenaAuthenticationManager(client_id, client_secret, api_key)
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=API_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make authenticated request to Gardena API with retry logic."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Ensure we have a valid token
                await self.auth_manager.authenticate()
                
                session = await self._get_session()
                headers = self.auth_manager.get_auth_headers()
                
                # Update headers with any provided headers
                if "headers" in kwargs:
                    headers.update(kwargs["headers"])
                    del kwargs["headers"]
                
                url = f"{API_BASE_URL}{endpoint}"
                
                _LOGGER.debug("Making API request: %s %s (attempt %d/%d)", method, url, attempt + 1, max_retries)
                
                async with session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug("API response status: %s, body: %s", response.status, response_text)
                    
                    if response.status in (200, 201, 202):
                        if response_text:
                            return await response.json()
                        return {}
                    
                    # Handle specific error codes
                    if response.status == 401:
                        _LOGGER.warning("Authentication failed (401), clearing tokens and retrying")
                        self.auth_manager.clear_tokens()
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise GardenaAPIError(
                                "Authentication failed after retries",
                                status_code=401
                            )
                    
                    elif response.status == 403:
                        error_data = None
                        try:
                            error_data = await response.json()
                        except Exception:
                            pass
                        raise GardenaAPIError(
                            "Access forbidden - insufficient permissions",
                            status_code=403,
                            response_data=error_data
                        )
                    
                    elif response.status == 404:
                        error_data = None
                        try:
                            error_data = await response.json()
                        except Exception:
                            pass
                        raise GardenaAPIError(
                            "Resource not found",
                            status_code=404,
                            response_data=error_data
                        )
                    
                    elif response.status in (500, 502):
                        error_data = None
                        try:
                            error_data = await response.json()
                        except Exception:
                            pass
                        
                        if attempt < max_retries - 1:
                            _LOGGER.warning("Server error %s, retrying in %s seconds", response.status, retry_delay)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            raise GardenaAPIError(
                                f"Server error after {max_retries} attempts",
                                status_code=response.status,
                                response_data=error_data
                            )
                    
                    else:
                        error_data = None
                        try:
                            error_data = await response.json()
                        except Exception:
                            pass
                        raise GardenaAPIError(
                            f"API request failed: {response.status} - {response_text}",
                            status_code=response.status,
                            response_data=error_data
                        )
                        
            except GardenaAuthError as e:
                _LOGGER.error("Authentication error: %s", e)
                raise GardenaAPIError(f"Authentication error: {e}") from e
            except aiohttp.ClientError as e:
                _LOGGER.error("Network error: %s", e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise GardenaAPIError(f"Network error after {max_retries} attempts: {e}") from e
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                raise GardenaAPIError(f"Unexpected error: {e}") from e
        
        # This should never be reached, but just in case
        raise GardenaAPIError(f"Request failed after {max_retries} attempts")

    async def get_locations(self) -> List[Dict[str, Any]]:
        """Get list of locations."""
        _LOGGER.debug("Fetching locations")
        try:
            data = await self._make_request("GET", "/locations")
            locations = data.get("data", [])
            _LOGGER.info("Successfully fetched %d locations", len(locations))
            return locations
        except Exception as e:
            _LOGGER.error("Failed to fetch locations: %s", e)
            raise

    async def get_location(self, location_id: str) -> Dict[str, Any]:
        """Get location with devices and services."""
        _LOGGER.debug("Fetching location %s", location_id)
        try:
            data = await self._make_request("GET", f"/locations/{location_id}")
            _LOGGER.info("Successfully fetched location %s", location_id)
            return data
        except Exception as e:
            _LOGGER.error("Failed to fetch location %s: %s", location_id, e)
            raise

    async def send_command(self, service_id: str, command_data: Dict[str, Any]) -> None:
        """Send command to device service."""
        _LOGGER.debug("Sending command to service %s: %s", service_id, command_data)
        try:
            await self._make_request(
                "PUT",
                f"/command/{service_id}",
                json={"data": command_data},
            )
            _LOGGER.info("Successfully sent command to service %s", service_id)
        except Exception as e:
            _LOGGER.error("Failed to send command to service %s: %s", service_id, e)
            raise

    async def create_websocket_url(self, location_id: str) -> Dict[str, Any]:
        """Create WebSocket URL for real-time updates."""
        _LOGGER.debug("Creating WebSocket URL for location %s", location_id)
        try:
            websocket_data = {
                "data": {
                    "id": "websocket-request",
                    "type": "WEBSOCKET",
                    "attributes": {
                        "locationId": location_id
                    }
                }
            }
            
            data = await self._make_request(
                "POST",
                "/websocket",
                json=websocket_data,
            )
            _LOGGER.info("Successfully created WebSocket URL for location %s", location_id)
            return data
        except Exception as e:
            _LOGGER.error("Failed to create WebSocket URL for location %s: %s", location_id, e)
            raise

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        _LOGGER.debug("Closing Gardena Smart System client")
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        await self.auth_manager.close() 