"""Client for Gardena Smart System API."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any, Dict, List, Optional

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemClient:
    """Client for Gardena Smart System API."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        """Initialize the client."""
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            )
        return self._session

    async def _authenticate(self) -> None:
        """Authenticate with Gardena Smart System API."""
        if self._access_token:
            return

        session = await self._get_session()
        
        # This is a simplified authentication - in a real implementation,
        # you would need to implement OAuth2 flow with Gardena
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            async with session.post(
                f"{API_BASE_URL}/oauth2/token",
                data=auth_data,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data.get("access_token")
                    if not self._access_token:
                        raise Exception("No access token received")
                else:
                    raise Exception(f"Authentication failed: {response.status}")
        except Exception as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise

    async def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Make authenticated request to Gardena API."""
        await self._authenticate()
        
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/vnd.api+json",
        }
        
        url = f"{API_BASE_URL}{endpoint}"
        
        try:
            async with session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                if response.status in (200, 201):
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API request failed: {response.status} - {error_text}")
        except Exception as e:
            _LOGGER.error("API request failed: %s", e)
            raise

    async def get_locations(self) -> List[Dict[str, Any]]:
        """Get list of locations."""
        data = await self._make_request("GET", "/locations")
        return data.get("data", [])

    async def get_location(self, location_id: str) -> Dict[str, Any]:
        """Get location with devices and services."""
        return await self._make_request("GET", f"/locations/{location_id}")

    async def send_command(self, service_id: str, command_data: Dict[str, Any]) -> None:
        """Send command to device service."""
        await self._make_request(
            "PUT",
            f"/command/{service_id}",
            json={"data": command_data},
        )

    async def close(self) -> None:
        """Close the client session."""
        if self._session:
            await self._session.close()
            self._session = None 