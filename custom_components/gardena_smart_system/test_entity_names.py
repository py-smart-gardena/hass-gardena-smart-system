"""Entity names are translated, and entity IDs stay the English ones (#408).

The names were fixed English strings with the device name typed in. They come
from the translations now: Home Assistant puts the device name in front, and
on a controller with several valves the valve's name leads ("Lawn error").

Home Assistant builds a new entity's ID from its name in the installation's
language, German among them. Each entity suggests the ID its English name gave
before, so a new install gets the same IDs in every language.
"""

from unittest.mock import Mock

import pytest
from pytest_homeassistant.common import MockConfigEntry, MockEntityPlatform

from .binary_sensor import GardenaValveProblemSensor
from .const import CONF_VALVE_DURATIONS, DOMAIN
from .lawn_mower import GardenaLawnMower
from .models import (
    GardenaCommonService,
    GardenaDevice,
    GardenaMowerService,
    GardenaPowerSocketService,
    GardenaValveService,
)
from .number import GardenaValveDurationNumber
from .sensor import (
    GardenaBatterySensor,
    GardenaValveActivitySensor,
    GardenaValveErrorSensor,
)
from .switch import GardenaPowerSocketSwitch
from .valve import GardenaSmartIrrigationControl, GardenaWaterControl


def _device(device_id, name, model, services):
    common = GardenaCommonService(
        id=device_id, type="COMMON", device_id=device_id, name=name,
        model_type=model, rf_link_state="ONLINE", battery_level=80,
    )
    return GardenaDevice(
        id=device_id, name=name, model_type=model, serial="1",
        services={"COMMON": [common], **services}, location_id="loc",
    )


def _coordinator(*devices):
    by_id = {device.id: device for device in devices}
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.websocket_client = None
    coordinator.locations = {"loc": Mock(devices=by_id)}
    coordinator.get_device_by_id = Mock(side_effect=by_id.get)
    return coordinator


def _controller():
    lawn = GardenaValveService(id="sic:1", type="VALVE", device_id="sic", name="Lawn")
    hedge = GardenaValveService(id="sic:2", type="VALVE", device_id="sic", name="Hedge")
    return _device("sic", "Garden", "SMART_IRRIGATION_CONTROL", {"VALVE": [lawn, hedge]})


def _water_control():
    tap = GardenaValveService(id="wc:1", type="VALVE", device_id="wc", name="Balcony")
    return _device("wc", "Balcony", "WATER_CONTROL", {"VALVE": [tap]})


def _mower():
    mower = GardenaMowerService(id="mw", type="MOWER", device_id="mw", activity="PARKED_TIMER")
    return _device("mw", "Sileno", "MOWER", {"MOWER": [mower]})


def _socket():
    power = GardenaPowerSocketService(id="ps", type="POWER_SOCKET", device_id="ps", activity="OFF")
    return _device("ps", "Pump", "Smart Power Adapter", {"POWER_SOCKET": [power]})


async def _add(hass, domain, entities):
    """Add entities the way the integration's platform does, translations loaded."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    platform = MockEntityPlatform(hass, domain=domain, platform_name=DOMAIN)
    platform.config_entry = entry
    await platform.platform_data.async_load_translations()
    await platform.async_add_entities(entities)
    return {
        entity.entity_id: hass.states.get(entity.entity_id).attributes["friendly_name"]
        for entity in entities
    }


def _entities(hass_language):
    controller, tap, mower, socket = _controller(), _water_control(), _mower(), _socket()
    coordinator = _coordinator(controller, tap, mower, socket)
    lawn, _hedge = controller.services["VALVE"]
    return {
        "sensor": [
            GardenaValveErrorSensor(coordinator, controller, lawn),
            GardenaValveActivitySensor(coordinator, controller, lawn),
            GardenaValveErrorSensor(coordinator, tap, tap.services["VALVE"][0]),
            GardenaBatterySensor(coordinator, tap, tap.services["COMMON"][0]),
        ],
        "binary_sensor": [GardenaValveProblemSensor(coordinator, controller, lawn)],
        "number": [GardenaValveDurationNumber(coordinator, controller, lawn)],
        "valve": [
            GardenaSmartIrrigationControl(coordinator, controller, lawn),
            GardenaWaterControl(coordinator, tap, tap.services["VALVE"][0]),
        ],
        "lawn_mower": [GardenaLawnMower(coordinator, mower, mower.services["MOWER"][0])],
        "switch": [GardenaPowerSocketSwitch(coordinator, socket, socket.services["POWER_SOCKET"][0])],
    }


# entity ID -> friendly name, in English and in German. The IDs are the ones
# the English names gave before, in both.
EXPECTED = {
    "sensor.lawn_error": ("Garden Lawn error", "Garden Lawn Fehler"),
    "sensor.lawn_activity": ("Garden Lawn activity", "Garden Lawn Aktivität"),
    "sensor.balcony_error": ("Balcony Error", "Balcony Fehler"),
    "sensor.balcony_battery_level": ("Balcony Battery level", "Balcony Batteriestand"),
    "binary_sensor.lawn_problem": ("Garden Lawn problem", "Garden Lawn Problem"),
    "number.garden_lawn_watering_duration": (
        "Garden Lawn watering duration",
        "Garden Lawn Bewässerungsdauer",
    ),
    "valve.garden_lawn": ("Garden Lawn", "Garden Lawn"),
    "valve.balcony": ("Balcony", "Balcony"),
    "lawn_mower.sileno_lawn_mower": ("Sileno", "Sileno"),
    "switch.pump_power_socket": ("Pump Power socket", "Pump Steckdose"),
}


@pytest.mark.parametrize(("language", "column"), [("en", 0), ("de", 1)])
async def test_names_are_translated_and_ids_stay(hass, language, column):
    hass.config.language = language
    # What the number platform's setup leaves for its entities.
    hass.data.setdefault(DOMAIN, {})[CONF_VALVE_DURATIONS] = {}
    seen = {}
    for domain, entities in _entities(language).items():
        seen.update(await _add(hass, domain, entities))

    assert seen == {entity_id: names[column] for entity_id, names in EXPECTED.items()}


def test_every_name_key_is_in_english_and_german():
    """A key missing in English shows no name at all; German is checked too."""
    import json
    from pathlib import Path

    here = Path(__file__).parent
    for name in ("strings.json", "translations/en.json", "translations/de.json"):
        entity = json.loads((here / name).read_text("utf-8"))["entity"]
        keys = {(platform, key) for platform, keys in entity.items() for key in keys}
        for platform, key in [
            ("sensor", "battery_level"), ("sensor", "valve_error"), ("sensor", "valve_error_of"),
            ("sensor", "watering_end"), ("sensor", "watering_end_of"),
            ("sensor", "valve_activity"), ("sensor", "valve_activity_of"),
            ("sensor", "operating_hours"), ("sensor", "rf_link_quality"),
            ("sensor", "soil_temperature"), ("sensor", "ambient_temperature"),
            ("sensor", "soil_humidity"), ("sensor", "light_intensity"),
            ("binary_sensor", "online"), ("binary_sensor", "websocket_connected"),
            ("binary_sensor", "valve_problem"), ("binary_sensor", "valve_problem_of"),
            ("button", "start_mowing_now"), ("button", "return_to_dock"),
            ("button", "park_until_further_notice"),
            ("number", "watering_duration"), ("number", "watering_duration_of"),
            ("switch", "power_socket"),
        ]:
            assert (platform, key) in keys, f"{name}: {platform}.{key}"
            assert entity[platform][key]["name"], f"{name}: {platform}.{key}"
