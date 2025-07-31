"""Data coordinator for Gardena Smart System."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .gardena_client import GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Gardena Smart System data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        
        self.entry = entry
        self.client = GardenaSmartSystemClient(
            client_id=entry.data["client_id"],
            client_secret=entry.data["client_secret"],
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via Gardena Smart System API."""
        try:
            # Get locations and devices
            locations = await self.client.get_locations()
            
            if not locations:
                _LOGGER.warning("No locations found for Gardena Smart System")
                return {}
            
            # For now, we'll use the first location
            location_id = locations[0]["id"]
            location_data = await self.client.get_location(location_id)
            
            return {
                "locations": locations,
                "devices": location_data.get("included", []),
                "location_id": location_id,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating Gardena Smart System data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if hasattr(self.client, 'close'):
            await self.client.close() 