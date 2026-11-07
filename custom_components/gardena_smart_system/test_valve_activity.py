"""A valve's activity as a sensor: closed, manual or scheduled watering (#408)."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from homeassistant.components.sensor import SensorDeviceClass

from .const import VALVE_ACTIVITIES
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice, GardenaValveService
from .sensor import GardenaValveActivitySensor


def _sensor(activity="CLOSED", found=True):
    valve_service = GardenaValveService(
        id="device-1:1",
        type="VALVE",
        device_id="device-1",
        name="Lawn",
        state="OK",
        activity=activity,
    )
    device = Mock(spec=GardenaDevice)
    device.id = "device-1"
    device.name = "Irrigation"
    device.serial = "12345"
    device.model_type = "Smart Irrigation Control"
    device.services = {"VALVE": [valve_service]}
    coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    coordinator.last_update_success = True
    coordinator.get_device_by_id.return_value = device if found else None
    return GardenaValveActivitySensor(coordinator, device, valve_service), valve_service


@pytest.mark.parametrize(
    ("activity", "expected"),
    [
        ("CLOSED", "closed"),
        ("MANUAL_WATERING", "manual_watering"),
        ("SCHEDULED_WATERING", "scheduled_watering"),
    ],
)
def test_the_activity_is_reported(activity, expected):
    sensor, _ = _sensor(activity)

    assert sensor.native_value == expected


def test_a_schedule_from_the_app_reads_differently_from_a_command():
    """What the valve entity alone can't show: both are just "open" there."""
    sensor, service = _sensor("MANUAL_WATERING")
    manual = sensor.native_value

    service.activity = "SCHEDULED_WATERING"

    assert sensor.native_value != manual


def test_an_activity_the_api_added_later_is_no_value():
    """An enum sensor may only report one of its options."""
    sensor, _ = _sensor("SOMETHING_NEW")

    assert sensor.native_value is None


def test_no_activity_or_no_fresh_service_is_no_value():
    assert _sensor(None)[0].native_value is None
    assert _sensor("CLOSED", found=False)[0].native_value is None


def test_it_is_an_enum_sensor_with_a_stable_id():
    sensor, _ = _sensor()

    assert sensor.device_class == SensorDeviceClass.ENUM
    assert sensor.options == list(VALVE_ACTIVITIES)
    assert sensor.unique_id == "device-1_device-1:1_activity"


@pytest.mark.parametrize("path", ["strings.json", "translations/en.json", "translations/de.json"])
def test_every_activity_has_a_text(path):
    texts = json.loads((Path(__file__).parent / path).read_text(encoding="utf-8"))
    states = texts["entity"]["sensor"]["valve_activity"]["state"]

    assert set(states) == set(VALVE_ACTIVITIES)
