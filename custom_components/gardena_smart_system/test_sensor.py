"""Tests for Gardena Smart System sensors."""

import pytest
from unittest.mock import Mock

from .sensor import async_setup_entry, GardenaBatterySensor
from .const import DOMAIN
from .models import GardenaLocation, GardenaDevice, GardenaCommonService
from .coordinator import GardenaSmartSystemCoordinator


@pytest.mark.asyncio
async def test_battery_sensor_created_when_level_only():
    """Ensure battery sensor is created when battery level is reported without state."""
    # Create mock hass and config entry
    hass = Mock()
    entry = Mock()
    entry.entry_id = "test-entry"

    # Setup coordinator with device that has battery level but no state
    coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    common = GardenaCommonService(
        id="common-1",
        type="COMMON",
        device_id="device-1",
        battery_level=55,
        battery_state=None,
    )
    device = GardenaDevice(
        id="device-1",
        name="Water Control",
        model_type="",  # model_type not relevant for test
        serial="",
        services={"COMMON": [common]},
        location_id="loc-1",
    )
    location = GardenaLocation(id="loc-1", name="Garden", devices={"device-1": device})
    coordinator.locations = {"loc-1": location}
    coordinator.get_device_by_id.return_value = device

    hass.data = {DOMAIN: {entry.entry_id: coordinator}}

    added_entities = []

    async def _add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, entry, _add_entities)

    # One battery sensor should be created
    battery_entities = [
        e for e in added_entities if isinstance(e, GardenaBatterySensor)
    ]
    assert len(battery_entities) == 1
    assert battery_entities[0].native_value == 55
