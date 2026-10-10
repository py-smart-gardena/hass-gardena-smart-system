"""Tests for the Gardena lawn mower entity."""
import pytest
from unittest.mock import AsyncMock, Mock

from homeassistant.components.lawn_mower import LawnMowerActivity

from .coordinator import GardenaSmartSystemCoordinator
from .lawn_mower import GardenaLawnMower
from .models import GardenaDevice, GardenaMowerService


class TestGardenaLawnMowerActivity:
    """Test the activity mapping of GardenaLawnMower."""

    def _make_entity(self, activity, state, last_error_code="NO_MESSAGE"):
        """Build a lawn mower entity wired to a mower service with given values."""
        mower_service = GardenaMowerService(
            id="mower-1",
            type="MOWER",
            device_id="device-1",
            state=state,
            activity=activity,
            last_error_code=last_error_code,
        )

        device = Mock(spec=GardenaDevice)
        device.id = "device-1"
        device.name = "Test Mower"
        device.serial = "12345"
        device.services = {"MOWER": [mower_service]}

        coordinator = Mock(spec=GardenaSmartSystemCoordinator)
        coordinator.last_update_success = True
        coordinator.websocket_client = None
        coordinator.get_device_by_id.return_value = device
        coordinator.locations = {}

        entity = GardenaLawnMower(coordinator, device, mower_service)
        # available property walks coordinator.locations; force it available so
        # we exercise the activity-mapping branch under test.
        type(entity).available = property(lambda self: True)
        return entity

    @pytest.mark.parametrize(
        "activity,expected",
        [
            ("OK_CUTTING", LawnMowerActivity.MOWING),
            ("OK_SEARCHING", LawnMowerActivity.RETURNING),
            ("OK_CHARGING", LawnMowerActivity.DOCKED),
            ("PARKED_TIMER", LawnMowerActivity.DOCKED),
            ("PAUSED", LawnMowerActivity.PAUSED),
        ],
    )
    def test_mapped_activities(self, activity, expected):
        """Known activities map regardless of the service state field."""
        entity = self._make_entity(activity, state="OK")
        assert entity.activity == expected

    def test_none_activity_without_error_state_is_paused(self):
        """NONE activity with a non-error state must not be reported as ERROR.

        Regression test for #375: mower stopped in the garden out of battery
        reports activity NONE but state OK / no error code. It should fall back
        to PAUSED rather than contradicting the mower_error sensor.
        """
        entity = self._make_entity("NONE", state="OK")
        assert entity.activity == LawnMowerActivity.PAUSED

    def test_unmapped_activity_without_error_state_is_paused(self):
        """An unknown future activity with a healthy state falls back to PAUSED."""
        entity = self._make_entity("SOME_NEW_ACTIVITY", state="OK")
        assert entity.activity == LawnMowerActivity.PAUSED

    @pytest.mark.parametrize("state", ["ERROR", "WARNING"])
    def test_none_activity_with_actionable_error_is_error(self, state):
        """NONE activity is ERROR when the state flags one and the code is actionable."""
        entity = self._make_entity(
            "NONE", state=state, last_error_code="WHEEL_MOTOR_BLOCKED_LEFT"
        )
        assert entity.activity == LawnMowerActivity.ERROR

    @pytest.mark.parametrize("state", ["WARNING", "ERROR"])
    def test_none_activity_with_informational_code_is_not_error(self, state):
        """Informational last_error_code must not be reported as ERROR.

        Regression test for #375: a mower that has reached its daily operating
        limit reports activity NONE, state WARNING, last_error_code
        PARKED_DAILY_LIMIT_REACHED. The mower_error sensor treats that code as
        "no error", so the entity must not contradict it with ERROR even though
        the service state is WARNING.
        """
        entity = self._make_entity(
            "NONE", state=state, last_error_code="PARKED_DAILY_LIMIT_REACHED"
        )
        assert entity.activity == LawnMowerActivity.PAUSED


class TestGardenaLawnMowerStart:
    """Start button behaviour (#399)."""

    def _entity(self):
        activity = TestGardenaLawnMowerActivity()
        entity = activity._make_entity("PARKED_TIMER", state="OK")
        entity.coordinator.client = Mock()
        entity.coordinator.client.send_command = AsyncMock()
        entity.coordinator.async_request_refresh = AsyncMock()
        entity.coordinator.config_entry_id = "entry-1"
        entity.hass = Mock()
        return entity

    @pytest.mark.asyncio
    async def test_start_mowing_resumes_schedule_by_default(self):
        """The Start button keeps START_DONT_OVERRIDE unless options say otherwise."""
        entity = self._entity()
        entity.hass.config_entries.async_get_entry.return_value = None

        await entity.async_start_mowing()

        payload = entity.coordinator.client.send_command.await_args.args[1]
        attributes = payload["data"]["attributes"]
        assert attributes["command"] == "START_DONT_OVERRIDE"
        assert "seconds" not in attributes

    @pytest.mark.asyncio
    async def test_start_mowing_mow_now_uses_configured_duration(self):
        """Options can make Start mow immediately for a chosen duration (#399)."""
        entity = self._entity()
        entry = Mock()
        entry.options = {
            "start_mowing_behavior": "mow_now",
            "mow_now_duration": 7200,
        }
        entity.hass.config_entries.async_get_entry.return_value = entry

        await entity.async_start_mowing()

        payload = entity.coordinator.client.send_command.await_args.args[1]
        attributes = payload["data"]["attributes"]
        assert attributes["command"] == "START_SECONDS_TO_OVERRIDE"
        assert attributes["seconds"] == 7200

    @pytest.mark.asyncio
    async def test_start_automatic_still_resumes_schedule(self):
        """The start_automatic service stays available when Start means mow now."""
        entity = self._entity()
        entry = Mock()
        entry.options = {"start_mowing_behavior": "mow_now", "mow_now_duration": 7200}
        entity.hass.config_entries.async_get_entry.return_value = entry

        await entity.async_start_automatic()

        payload = entity.coordinator.client.send_command.await_args.args[1]
        assert payload["data"]["attributes"]["command"] == "START_DONT_OVERRIDE"
