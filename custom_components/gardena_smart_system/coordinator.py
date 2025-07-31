"""Data coordinator for Gardena Smart System."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .auth import GardenaAuthError
from .const import DOMAIN, UPDATE_INTERVAL
from .gardena_client import GardenaAPIError, GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemCoordinator(DataUpdateCoordinator):
    """Coordinator for Gardena Smart System data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GardenaSmartSystemClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self.locations: Dict[str, Any] = {}
        self.devices: Dict[str, Any] = {}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data from Gardena Smart System."""
        _LOGGER.debug("Starting data update from Gardena Smart System")
        
        try:
            # Get locations
            locations = await self.client.get_locations()
            self.locations = {loc["id"]: loc for loc in locations}
            
            # Get devices for each location
            all_devices = {}
            for location_id in self.locations:
                try:
                    location_data = await self.client.get_location(location_id)
                    if "included" in location_data:
                        devices = {}
                        for item in location_data["included"]:
                            if item["type"] == "DEVICE":
                                device_id = item["id"]
                                devices[device_id] = item
                        all_devices[location_id] = devices
                except Exception as e:
                    _LOGGER.warning(f"Failed to get devices for location {location_id}: {e}")
                    all_devices[location_id] = {}
            
            self.devices = all_devices
            
            _LOGGER.debug("Successfully updated Gardena Smart System data")
            return {
                "locations": self.locations,
                "devices": self.devices,
            }
            
        except GardenaAuthError as err:
            _LOGGER.error("Authentication error during data update: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except GardenaAPIError as err:
            _LOGGER.error("API error during data update: %s (status: %s)", err, err.status_code)
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error during data update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.debug("Shutting down Gardena Smart System coordinator")
        if self.client:
            await self.client.close() 