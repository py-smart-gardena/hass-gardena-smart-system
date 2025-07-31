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
from .gardena_client import GardenaSmartSystemClient, GardenaAPIError
from .auth import GardenaAuthError

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
            _LOGGER.debug("Starting data update for Gardena Smart System")
            
            # Get locations and devices
            locations = await self.client.get_locations()
            
            if not locations:
                _LOGGER.warning("No locations found for Gardena Smart System")
                return {
                    "locations": [],
                    "devices": [],
                    "location_id": None,
                }
            
            # For now, we'll use the first location
            location_id = locations[0]["id"]
            _LOGGER.debug("Using location: %s", location_id)
            
            location_data = await self.client.get_location(location_id)
            devices = location_data.get("included", [])
            
            _LOGGER.info("Successfully updated data: %d locations, %d devices", len(locations), len(devices))
            
            return {
                "locations": locations,
                "devices": devices,
                "location_id": location_id,
            }
            
        except GardenaAuthError as err:
            _LOGGER.error("Authentication error during data update: %s (status: %s)", err, err.status_code)
            raise UpdateFailed(f"Authentication error: {err}") from err
            
        except GardenaAPIError as err:
            _LOGGER.error("API error during data update: %s (status: %s)", err, err.status_code)
            raise UpdateFailed(f"API error: {err}") from err
            
        except Exception as err:
            _LOGGER.error("Unexpected error during data update: %s", err, exc_info=True)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.debug("Shutting down Gardena Smart System coordinator")
        try:
            await self.client.close()
        except Exception as e:
            _LOGGER.error("Error during coordinator shutdown: %s", e) 