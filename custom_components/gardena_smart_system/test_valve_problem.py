"""A problem binary sensor per valve (#408)."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from .binary_sensor import GardenaValveProblemSensor
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaCommonService, GardenaDevice, GardenaValveService


def _sensor(state="OK", error_code=None, found=True):
    valve_service = GardenaValveService(
        id="device-1:1",
        type="VALVE",
        device_id="device-1",
        name="Lawn",
        state=state,
        activity="CLOSED",
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
    coordinator.get_device_by_id.return_value = device if found else None
    return GardenaValveProblemSensor(coordinator, device, valve_service)


@pytest.mark.parametrize("state", ["WARNING", "ERROR"])
def test_a_warning_or_error_is_a_problem(state):
    assert _sensor(state, "VALVE_BROKEN").is_on is True


def test_a_valve_that_is_ok_is_no_problem():
    assert _sensor("OK", "NO_MESSAGE").is_on is False


def test_an_error_code_left_from_an_earlier_run_is_no_problem():
    """The API asks to look at lastErrorCode only in WARNING or ERROR."""
    sensor = _sensor("OK", "WATERING_CANCELED")

    assert sensor.is_on is False
    assert sensor.extra_state_attributes["error_code"] == "watering_canceled"


def test_the_attributes_name_the_state_and_the_code():
    attrs = _sensor("ERROR", "VALVE_BROKEN").extra_state_attributes

    assert attrs["state"] == "ERROR"
    assert attrs["error_code"] == "valve_broken"


def test_an_output_without_a_valve_is_unavailable_not_a_problem():
    """As the valve itself since #409."""
    assert _sensor("UNAVAILABLE").available is False


def test_no_fresh_service_is_no_value():
    assert _sensor(found=False).is_on is None


def test_it_is_a_problem_sensor_with_a_stable_id():
    sensor = _sensor()

    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
    assert sensor.unique_id == "device-1_device-1:1_problem"


@pytest.mark.parametrize("path", ["strings.json", "translations/en.json", "translations/de.json"])
def test_it_has_a_name_in_the_texts(path):
    texts = json.loads((Path(__file__).parent / path).read_text(encoding="utf-8"))

    assert texts["entity"]["binary_sensor"]["valve_problem"]["name"]
