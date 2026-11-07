"""Diagnostics download with credentials redacted (#408)."""
import json
from unittest.mock import Mock

from homeassistant.components.diagnostics import REDACTED

from .api_tracker import APIRequestTracker
from .diagnostics import async_get_config_entry_diagnostics
from .models import (
    GardenaCommonService,
    GardenaDevice,
    GardenaLocation,
    GardenaValveService,
)

SECRET = "s3cr3t-client-secret"
CLIENT = "my-client-id"
SERIAL = "12345678"


def _setup():
    common = GardenaCommonService(
        id="device-1",
        type="COMMON",
        device_id="device-1",
        name="Irrigation",
        rf_link_state="ONLINE",
        serial=SERIAL,
    )
    valve = GardenaValveService(
        id="device-1:1",
        type="VALVE",
        device_id="device-1",
        name="Lawn",
        state="OK",
        activity="CLOSED",
    )
    device = GardenaDevice(
        id="device-1",
        name="Irrigation",
        model_type="Smart Irrigation Control",
        serial=SERIAL,
        services={"COMMON": [common], "VALVE": [valve]},
        location_id="location-1",
    )
    location = GardenaLocation(id="location-1", name="Garden Miller", devices={device.id: device})

    tracker = APIRequestTracker()
    tracker.record("GET", "/locations", 200, source="client")

    websocket = Mock()
    websocket.connection_status = "connected"
    websocket.is_connected = True
    websocket.is_connecting = False
    websocket.reconnect_attempts = 0
    websocket.websocket_url = "wss://api.smart.gardena.dev/v1/websocket/TOKEN"

    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.locations = {location.id: location}
    coordinator.websocket_client = websocket
    coordinator.client = Mock()
    coordinator.client.api_tracker = tracker

    entry = Mock()
    entry.entry_id = "entry-1"
    entry.data = {"client_id": CLIENT, "client_secret": SECRET}
    entry.options = {"valve_durations": {"device-1:1": 30}}

    hass = Mock()
    hass.data = {"gardena_smart_system": {"entry-1": coordinator}}
    return hass, entry


async def test_the_credentials_are_redacted():
    hass, entry = _setup()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"] == {
        "client_id": REDACTED,
        "client_secret": REDACTED,
    }


async def test_nothing_secret_is_left_anywhere():
    """Serials, the WebSocket token and the garden name don't leak."""
    hass, entry = _setup()

    text = json.dumps(await async_get_config_entry_diagnostics(hass, entry))

    for secret in (SECRET, CLIENT, SERIAL, "TOKEN", "Garden Miller"):
        assert secret not in text


async def test_the_devices_and_services_are_there_for_troubleshooting():
    hass, entry = _setup()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    device = diagnostics["locations"][0]["devices"][0]
    assert device["model_type"] == "Smart Irrigation Control"
    assert device["serial"] == REDACTED
    valve = device["services"]["VALVE"][0]
    assert valve["id"] == "device-1:1"
    assert valve["state"] == "OK"
    assert valve["activity"] == "CLOSED"
    assert diagnostics["entry"]["options"] == {"valve_durations": {"device-1:1": 30}}


async def test_the_websocket_and_the_api_usage_are_reported():
    hass, entry = _setup()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["websocket"] == {
        "status": "connected",
        "is_connected": True,
        "is_connecting": False,
        "reconnect_attempts": 0,
    }
    assert diagnostics["api_usage"]["requests_this_week"] == 1
    assert diagnostics["coordinator"]["last_update_success"] is True


async def test_an_entry_that_is_not_loaded_still_gives_its_settings():
    hass, entry = _setup()
    hass.data = {"gardena_smart_system": {}}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"]["client_secret"] == REDACTED
    assert "locations" not in diagnostics
