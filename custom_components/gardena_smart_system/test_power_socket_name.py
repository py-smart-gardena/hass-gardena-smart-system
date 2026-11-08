"""The power socket's name carries the device name once, not twice."""
from unittest.mock import Mock

from pytest_homeassistant.common import (
    MockConfigEntry,
    MockEntityPlatform,
)

from .const import DOMAIN
from .models import GardenaCommonService, GardenaDevice, GardenaPowerSocketService
from .switch import GardenaPowerSocketSwitch


def _socket():
    common = GardenaCommonService(
        id="dev-1", type="COMMON", device_id="dev-1", name="Pump",
        model_type="Smart Power Adapter", rf_link_state="ONLINE",
    )
    power = GardenaPowerSocketService(
        id="dev-1", type="POWER_SOCKET", device_id="dev-1", activity="OFF",
    )
    device = GardenaDevice(
        id="dev-1", name="Pump", model_type="Smart Power Adapter", serial="1",
        services={"COMMON": [common], "POWER_SOCKET": [power]}, location_id="loc",
    )
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.websocket_client = None
    coordinator.locations = {"loc": Mock(devices={"dev-1": device})}
    coordinator.get_device_by_id = Mock(return_value=device)
    return GardenaPowerSocketSwitch(coordinator, device, power)


async def test_the_socket_is_named_after_its_device_once(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    platform = MockEntityPlatform(hass, domain="switch", platform_name=DOMAIN)
    platform.config_entry = entry
    socket = _socket()

    await platform.async_add_entities([socket])

    state = hass.states.get(socket.entity_id)
    assert state.attributes["friendly_name"] == "Pump Power Socket"
    assert socket.entity_id == "switch.pump_power_socket"
