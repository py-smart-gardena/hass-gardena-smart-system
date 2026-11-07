"""The valve actions take a valve entity as target (#408)."""
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.exceptions import HomeAssistantError

from . import services as services_module
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice, GardenaValveService
from .services import (
    SERVICE_SCHEMA_VALVE,
    SERVICE_SCHEMA_VALVE_BASE,
    SERVICE_SCHEMA_VALVE_PAUSE,
    GardenaServiceManager,
)


def _registry(entries):
    """An entity registry knowing the given entity ids."""
    registry = Mock()
    registry.async_get.side_effect = lambda entity_id: entries.get(entity_id)
    return registry


def _entry(unique_id, platform="gardena_smart_system", domain="valve"):
    return Mock(unique_id=unique_id, platform=platform, domain=domain)


@pytest.fixture
def manager(monkeypatch):
    """A controller with two outputs and a Water Control, and their entities."""
    controller = Mock(spec=GardenaDevice)
    controller.id = "controller-1"
    out1 = Mock(spec=GardenaValveService)
    out1.id = "controller-1:1"
    out2 = Mock(spec=GardenaValveService)
    out2.id = "controller-1:2"
    controller.services = {"VALVE": [out1, out2]}

    tap = Mock(spec=GardenaDevice)
    tap.id = "tap-1"
    tap_valve = Mock(spec=GardenaValveService)
    tap_valve.id = "tap-1:1"
    tap.services = {"VALVE": [tap_valve]}

    location = Mock()
    location.devices = {controller.id: controller, tap.id: tap}
    coordinator = Mock(spec=GardenaSmartSystemCoordinator)
    coordinator.locations = {"location-1": location}
    coordinator.client = Mock()
    coordinator.client.send_command = AsyncMock(return_value={"status": "accepted"})
    coordinator.get_device_by_id.side_effect = lambda device_id: location.devices.get(device_id)

    hass = Mock()
    hass.services = Mock()
    hass.services.async_register = Mock()
    hass.data = {"gardena_smart_system": {"entry-1": coordinator}}

    registry = _registry(
        {
            "valve.lawn": _entry("controller-1_controller-1:1"),
            "valve.hedge": _entry("controller-1_controller-1:2"),
            "valve.balcony": _entry("tap-1_water_control"),
            "valve.other": _entry("abc", platform="rainbird"),
            "valve.gone": _entry("controller-1_controller-1:9"),
        }
    )
    monkeypatch.setattr(services_module.er, "async_get", lambda hass: registry)
    # A Gardena device id passed as device_id is not in the device registry.
    monkeypatch.setattr(services_module.dr, "async_get", lambda hass: _registry({}))
    return GardenaServiceManager(hass), coordinator


def _sent(coordinator):
    return [call.args[0] for call in coordinator.client.send_command.await_args_list]


def _call(**data):
    call = Mock()
    call.data = data
    return call


async def test_opening_a_valve_by_its_entity(manager):
    service_manager, coordinator = manager

    await service_manager._service_valve_open(_call(entity_id=["valve.hedge"], duration=600))

    assert _sent(coordinator) == ["controller-1:2"]
    payload = coordinator.client.send_command.await_args.args[1]
    assert payload["data"]["attributes"]["seconds"] == 600


async def test_several_entities_are_each_closed(manager):
    service_manager, coordinator = manager

    await service_manager._service_valve_close(_call(entity_id=["valve.lawn", "valve.balcony"]))

    assert _sent(coordinator) == ["controller-1:1", "tap-1:1"]


async def test_a_water_control_entity_targets_its_one_valve(manager):
    service_manager, coordinator = manager

    await service_manager._service_valve_pause(_call(entity_id=["valve.balcony"]))

    assert _sent(coordinator) == ["tap-1:1"]


async def test_the_entity_wins_over_a_device(manager):
    """Without it, the device would fan out to both outputs."""
    service_manager, coordinator = manager

    await service_manager._service_valve_unpause(
        _call(entity_id=["valve.lawn"], device_id="controller-1")
    )

    assert _sent(coordinator) == ["controller-1:1"]


@pytest.mark.parametrize("entity_id", ["valve.other", "valve.unknown", "valve.gone"])
async def test_an_entity_that_is_no_gardena_valve_fails_the_call(manager, entity_id):
    service_manager, coordinator = manager

    with pytest.raises(HomeAssistantError):
        await service_manager._service_valve_close(_call(entity_id=[entity_id]))

    coordinator.client.send_command.assert_not_called()


async def test_service_id_and_device_id_work_as_before(manager):
    service_manager, coordinator = manager

    await service_manager._service_valve_close(_call(service_id="controller-1:2"))
    await service_manager._service_valve_pause(_call(device_id="controller-1"))

    assert _sent(coordinator) == ["controller-1:2", "controller-1:1", "controller-1:2"]


async def test_no_target_at_all_names_all_three(manager):
    service_manager, _ = manager

    with pytest.raises(HomeAssistantError, match="entity_id"):
        await service_manager._service_valve_close(_call())


@pytest.mark.parametrize(
    "schema", [SERVICE_SCHEMA_VALVE, SERVICE_SCHEMA_VALVE_BASE, SERVICE_SCHEMA_VALVE_PAUSE]
)
def test_the_schemas_take_one_entity_or_a_list(schema):
    assert schema({"entity_id": "valve.lawn"})["entity_id"] == ["valve.lawn"]
    assert schema({"entity_id": ["valve.lawn", "valve.hedge"]})["entity_id"] == [
        "valve.lawn",
        "valve.hedge",
    ]
