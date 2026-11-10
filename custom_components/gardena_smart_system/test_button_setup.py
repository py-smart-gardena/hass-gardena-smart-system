"""Tests for setting up the button platform (#421)."""
from unittest.mock import Mock

import pytest

from .button import async_setup_entry
from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice, GardenaMowerService


@pytest.mark.asyncio
async def test_setup_does_not_read_entity_names_before_entities_are_added():
    """Set up the buttons without touching name before they have platform data.

    Home Assistant 2026.11 resolves a translated name through the entity's
    platform data, which an entity only has once it is added. Reading
    entity.name in the setup log line raised AttributeError and the whole
    button platform failed to set up.
    """
    mower_service = GardenaMowerService(
        id="mower-1",
        type="MOWER",
        device_id="device-1",
        state="OK",
        activity="PARKED_TIMER",
        last_error_code="NO_MESSAGE",
    )
    device = Mock(spec=GardenaDevice)
    device.id = "device-1"
    device.name = "Test Mower"
    device.serial = "12345"
    device.services = {"MOWER": [mower_service]}

    location = Mock()
    location.devices = {"device-1": device}

    coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    coordinator.locations = {"location-1": location}
    coordinator.websocket_client = None
    coordinator.get_device_by_id.return_value = device

    entry = Mock()
    entry.entry_id = "entry-1"
    hass = Mock()
    hass.data = {DOMAIN: {"entry-1": coordinator}}
    added = []

    await async_setup_entry(hass, entry, added.extend)

    assert len(added) == 3
    assert all(entity.platform is None for entity in added)
