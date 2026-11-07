"""A valve shows "opening" or "closing" while a command is on its way (#408)."""
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.valve import ValveState

from . import valve as valve_module
from .const import DOMAIN, VALVE_COMMAND_PENDING_SECONDS
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaCommonService, GardenaDevice, GardenaValveService
from .valve import GardenaSmartIrrigationControl, GardenaWaterControl


class _Timer:
    """Stands in for async_call_later: records the call, can fire it."""

    def __init__(self):
        self.delay = None
        self.action = None
        self.cancel = Mock()

    def __call__(self, hass, delay, action):
        self.delay = delay
        self.action = action
        return self.cancel


@pytest.fixture
def timer(monkeypatch):
    timer = _Timer()
    monkeypatch.setattr(valve_module, "async_call_later", timer)
    return timer


def _valve(cls=GardenaSmartIrrigationControl, activity="CLOSED", error_code=None):
    valve_service = GardenaValveService(
        id="device-1:1",
        type="VALVE",
        device_id="device-1",
        name="Lawn",
        state="OK",
        activity=activity,
        last_error_code=error_code,
    )
    common = GardenaCommonService(
        id="device-1", type="COMMON", device_id="device-1", rf_link_state="ONLINE"
    )
    device = Mock(spec=GardenaDevice)
    device.id = "device-1"
    device.name = "Irrigation"
    device.serial = "12345"
    device.model_type = "Smart Irrigation Control"
    device.services = {"VALVE": [valve_service], "COMMON": [common]}

    location = Mock()
    location.devices = {device.id: device}
    coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    coordinator.last_update_success = True
    coordinator.websocket_client = None
    coordinator.locations = {"location-1": location}
    coordinator.get_device_by_id.return_value = device
    coordinator.client = Mock()
    coordinator.client.send_command = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.hass = Mock()
    coordinator.hass.data = {DOMAIN: {}}

    entity = cls(coordinator, device, valve_service)
    # A coordinator update writes the state, which needs a running hass.
    entity.async_write_ha_state = Mock()
    return entity, valve_service


def _report(entity, valve_service, activity=None, error_code=None):
    """The WebSocket delivers the valve's new state."""
    if activity is not None:
        valve_service.activity = activity
    if error_code is not None:
        valve_service.last_error_code = error_code
    entity._handle_coordinator_update()


async def test_open_shows_opening_until_the_valve_reports_watering(timer):
    entity, service = _valve()

    await entity.async_open_valve()

    assert entity.is_opening is True
    assert entity.state == ValveState.OPENING
    assert timer.delay == VALVE_COMMAND_PENDING_SECONDS
    entity.coordinator.client.send_command.assert_awaited_once()

    _report(entity, service, activity="MANUAL_WATERING")

    assert entity.is_opening is False
    assert entity.state == ValveState.OPEN
    timer.cancel.assert_called_once()


async def test_an_unrelated_update_keeps_the_command_pending(timer):
    """The refresh right after the command still reports the old state."""
    entity, service = _valve()

    await entity.async_open_valve()
    _report(entity, service)

    assert entity.is_opening is True
    timer.cancel.assert_not_called()


async def test_close_shows_closing_until_the_valve_reports_closed(timer):
    entity, service = _valve(activity="MANUAL_WATERING")

    await entity.async_close_valve()

    assert entity.is_closing is True
    assert entity.state == ValveState.CLOSING

    _report(entity, service, activity="CLOSED")

    assert entity.is_closing is False
    assert entity.state == ValveState.CLOSED


async def test_a_command_that_fails_to_send_is_not_left_pending(timer):
    entity, _ = _valve()
    entity.coordinator.client.send_command.side_effect = RuntimeError("gateway")

    with pytest.raises(RuntimeError):
        await entity.async_open_valve()

    assert entity.is_opening is False
    timer.cancel.assert_called_once()


async def test_the_valve_refusing_with_an_error_code_ends_the_wait(timer):
    """For example CONCURRENT_LIMIT_REACHED: the valve will not open."""
    entity, service = _valve(error_code="NO_MESSAGE")

    await entity.async_open_valve()
    _report(entity, service, error_code="CONCURRENT_LIMIT_REACHED")

    assert entity.is_opening is False
    assert entity.state == ValveState.CLOSED


async def test_an_error_code_already_there_does_not_end_the_wait(timer):
    entity, service = _valve(error_code="VALVE_BROKEN")

    await entity.async_open_valve()
    _report(entity, service)

    assert entity.is_opening is True


async def test_no_report_in_time_gives_up(timer):
    entity, _ = _valve()

    await entity.async_open_valve()
    timer.action(None)

    assert entity.is_opening is False
    assert entity.state == ValveState.CLOSED


async def test_opening_a_valve_that_is_already_open_does_not_show_opening(timer):
    entity, _ = _valve(activity="SCHEDULED_WATERING")

    await entity.async_open_valve()

    assert entity.is_opening is False
    assert entity.state == ValveState.OPEN


async def test_water_control_shows_opening_too(timer):
    entity, service = _valve(cls=GardenaWaterControl)

    await entity.async_open_valve()
    assert entity.is_opening is True

    _report(entity, service, activity="MANUAL_WATERING")
    assert entity.is_opening is False


async def test_removing_the_entity_cancels_the_timer(timer):
    entity, _ = _valve()

    await entity.async_open_valve()
    await entity.async_will_remove_from_hass()

    timer.cancel.assert_called_once()
