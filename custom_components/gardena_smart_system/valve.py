"""Support for Gardena Smart System valves."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature, ValveDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_VALVE_DURATIONS,
    DEFAULT_VALVE_DURATION_SECONDS,
    DOMAIN,
    VALVE_COMMAND_PENDING_SECONDS,
)
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaEntity

_LOGGER = logging.getLogger(__name__)

# Activity values that mean the valve is open / watering
_OPEN_ACTIVITIES = ("MANUAL_WATERING", "SCHEDULED_WATERING")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System valves."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create valve entities for each device
    entities = []

    for location in coordinator.locations.values():
        for device in location.devices.values():
            _LOGGER.debug(
                "Checking device %s (%s) - Model: %s - Services: %s",
                device.name,
                device.id,
                getattr(device, "model_type", "Unknown"),
                list(device.services.keys()),
            )

            # Check if this is a Water Control (single valve device)
            if device.model_type == "WATER_CONTROL" and "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                if len(valve_services) == 1:
                    _LOGGER.info(f"Found Water Control device: {device.name} ({device.id})")
                    entities.append(GardenaWaterControl(coordinator, device, valve_services[0]))
                else:
                    _LOGGER.warning(f"Water Control device {device.name} has {len(valve_services)} valve services, expected 1")

            # Check if this is a Smart Irrigation Control (multiple valve device)
            elif device.model_type == "SMART_IRRIGATION_CONTROL" and "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                _LOGGER.info(f"Found Smart Irrigation Control device: {device.name} ({device.id}) with {len(valve_services)} valves")
                for valve_service in valve_services:
                    _LOGGER.info(f"Creating valve entity for Smart Irrigation Control: {valve_service.name} ({valve_service.id})")
                    entities.append(GardenaSmartIrrigationControl(coordinator, device, valve_service))

            # Fallback for other devices with VALVE services
            elif "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                _LOGGER.info(f"Found generic device with valves: {device.name} ({device.id}) with {len(valve_services)} valves")
                for valve_service in valve_services:
                    _LOGGER.info(f"Creating generic valve entity: {valve_service.name} ({valve_service.id})")
                    entities.append(GardenaValve(coordinator, device, valve_service))

    _LOGGER.info(f"Created {len(entities)} valve entities")
    async_add_entities(entities)


class _GardenaValveBase(GardenaEntity, ValveEntity):
    """Shared logic for all Gardena valve entities.

    Property getters (`is_closed`, `is_open`) are pure and side-effect free —
    Home Assistant calls them multiple times per update cycle (e.g. directly
    and via the chained `state` property of `ValveEntity`). Logging activity
    transitions belongs in the coordinator-update callback so each WebSocket
    event produces at most one log line per entity.
    """

    # Human-readable label used in log messages (overridden by subclasses).
    _log_label: str = "Valve"

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        super().__init__(coordinator, device, "VALVE")
        self.valve_service = valve_service
        self._last_logged_activity: str | None = None
        # A command sent and not yet seen through (#408): "opening" or
        # "closing", the error code when it was sent, and the timer that
        # gives up on it.
        self._pending: str | None = None
        self._pending_error_code: str | None = None
        self._pending_timeout: CALLBACK_TYPE | None = None

        # Set required attributes for valve entities
        self._attr_reports_position = False
        self._attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def _get_current_valve_service(self):
        """Get current valve service from coordinator (fresh data)."""
        device = self.coordinator.get_device_by_id(self.device.id)
        if device and "VALVE" in device.services:
            for service in device.services["VALVE"]:
                if service.id == self.valve_service.id:
                    return service
        return None

    @property
    def available(self) -> bool:
        """Return False when no valve is connected to this output.

        The API reports an output with nothing connected as a VALVE service in
        state UNAVAILABLE. Before V2 the valve entities took that from the valve
        service; since the V2 rewrite (#293) only the device is checked, so
        every output of a Smart Irrigation Control stays available (#409).
        """
        if not super().available:
            return False
        current_service = self._get_current_valve_service()
        return not (current_service and current_service.state == "UNAVAILABLE")

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            return current_service.activity == "CLOSED"
        return True

    @property
    def is_open(self) -> bool:
        """Return true if valve is open (watering)."""
        current_service = self._get_current_valve_service()
        if current_service and current_service.activity:
            return current_service.activity in _OPEN_ACTIVITIES
        return False

    @property
    def is_opening(self) -> bool:
        """Return true while an open command is on its way.

        The API has no opening state: the valve reports its new activity only
        once it has acted, seconds after the command. Until then the entity
        showed the old state, so a caller could not tell a pending command
        from a failed one, and some sent it again (#408).
        """
        return self._pending == "opening" and not self.is_open

    @property
    def is_closing(self) -> bool:
        """Return true while a close command is on its way."""
        return self._pending == "closing" and not self.is_closed

    def _start_pending(self, pending: str) -> None:
        """Show the command as on its way, until the valve reports it."""
        self._cancel_pending_timeout()
        current_service = self._get_current_valve_service()
        self._pending = pending
        self._pending_error_code = (
            current_service.last_error_code if current_service else None
        )
        self._pending_timeout = async_call_later(
            self.coordinator.hass,
            VALVE_COMMAND_PENDING_SECONDS,
            self._pending_timed_out,
        )
        self._write_state()

    def _clear_pending(self) -> None:
        """Stop showing a command as on its way."""
        self._cancel_pending_timeout()
        if self._pending is not None:
            self._pending = None
            self._write_state()

    def _cancel_pending_timeout(self) -> None:
        if self._pending_timeout is not None:
            self._pending_timeout()
            self._pending_timeout = None

    @callback
    def _pending_timed_out(self, _now) -> None:
        """No update reported the valve open or closed in time: give up."""
        self._pending_timeout = None
        if self._pending is not None:
            _LOGGER.warning(
                "%s %s did not report %s within %s s",
                self._log_label,
                self._attr_name,
                "open" if self._pending == "opening" else "closed",
                VALVE_COMMAND_PENDING_SECONDS,
            )
        self._clear_pending()

    def _pending_resolved(self) -> bool:
        """Whether the valve has done what the command asked, or refused it."""
        if self._pending == "opening" and self.is_open:
            return True
        if self._pending == "closing" and self.is_closed:
            return True
        # A new error code, such as CONCURRENT_LIMIT_REACHED or NOT_CONNECTED,
        # is the valve's answer that it will not.
        current_service = self._get_current_valve_service()
        error_code = current_service.last_error_code if current_service else None
        return error_code not in (None, "NO_MESSAGE", self._pending_error_code)

    def _write_state(self) -> None:
        if self.hass is not None:
            self.async_write_ha_state()

    async def _async_send_valve_command(self, command_data: dict, pending: str) -> None:
        """Send a command, showing it as on its way until the valve reports it."""
        self._start_pending(pending)
        try:
            await self.coordinator.client.send_command(self.valve_service.id, command_data)
            await self.coordinator.async_request_refresh()
        except Exception:
            self._clear_pending()
            raise

    async def async_will_remove_from_hass(self) -> None:
        """Cancel a pending command's timer."""
        self._cancel_pending_timeout()
        await super().async_will_remove_from_hass()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = super().extra_state_attributes
        attrs["service_id"] = self.valve_service.id
        return attrs

    def _get_configured_duration_seconds(self) -> int:
        """Get the configured watering duration in seconds."""
        durations = self.coordinator.hass.data[DOMAIN].get(CONF_VALVE_DURATIONS, {})
        minutes = durations.get(self.valve_service.id)
        if minutes is not None:
            return int(minutes * 60)
        return DEFAULT_VALVE_DURATION_SECONDS

    @callback
    def _handle_coordinator_update(self) -> None:
        """Log activity transitions, then forward to the base class."""
        current_service = self._get_current_valve_service()
        activity = current_service.activity if current_service else None
        if activity != self._last_logged_activity:
            if self._last_logged_activity is None:
                _LOGGER.debug(
                    "%s %s initial activity: %s",
                    self._log_label,
                    self._attr_name,
                    activity,
                )
            else:
                _LOGGER.info(
                    "%s %s activity: %s -> %s",
                    self._log_label,
                    self._attr_name,
                    self._last_logged_activity,
                    activity,
                )
            self._last_logged_activity = activity
        if self._pending is not None and self._pending_resolved():
            self._cancel_pending_timeout()
            self._pending = None
        super()._handle_coordinator_update()


class GardenaWaterControl(_GardenaValveBase):
    """Representation of a Gardena Water Control (single valve device)."""

    _log_label = "Water Control"

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the Water Control."""
        super().__init__(coordinator, device, valve_service)
        self._attr_name = device.name  # Use device name, not service name
        self._attr_unique_id = f"{device.id}_water_control"
        self._attr_device_class = ValveDeviceClass.WATER

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"Opening Water Control {self.device.name} ({self.valve_service.id})")
        if not self.valve_service:
            _LOGGER.error(f"No valve service available for Water Control {self.device.name}")
            return
        seconds = self._get_configured_duration_seconds()
        command_data = {
            "data": {
                "id": "open_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "START_SECONDS_TO_OVERRIDE",
                    "seconds": seconds,
                },
            }
        }
        try:
            await self._async_send_valve_command(command_data, "opening")
        except Exception as e:
            _LOGGER.error(f"Error opening Water Control {self.device.name}: {e}")
            raise

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"Closing Water Control {self.device.name} ({self.valve_service.id})")
        if not self.valve_service:
            _LOGGER.error(f"No valve service available for Water Control {self.device.name}")
            return
        command_data = {
            "data": {
                "id": "close_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "STOP_UNTIL_NEXT_TASK",
                },
            }
        }
        try:
            await self._async_send_valve_command(command_data, "closing")
        except Exception as e:
            _LOGGER.error(f"Error closing Water Control {self.device.name}: {e}")
            raise


class GardenaSmartIrrigationControl(_GardenaValveBase):
    """Representation of a Gardena Smart Irrigation Control valve (multiple valve device)."""

    _log_label = "Smart Irrigation Control valve"

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the Smart Irrigation Control valve."""
        super().__init__(coordinator, device, valve_service)
        self._attr_name = f"{device.name} - {valve_service.name}"
        self._attr_unique_id = f"{device.id}_{valve_service.id}"
        self._attr_device_class = ValveDeviceClass.WATER

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"Opening Smart Irrigation Control valve {self._attr_name} ({self.valve_service.id})")
        if not self.valve_service:
            _LOGGER.error(f"No valve service available for Smart Irrigation Control valve {self._attr_name}")
            return
        seconds = self._get_configured_duration_seconds()
        command_data = {
            "data": {
                "id": "open_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "START_SECONDS_TO_OVERRIDE",
                    "seconds": seconds,
                },
            }
        }
        try:
            await self._async_send_valve_command(command_data, "opening")
        except Exception as e:
            _LOGGER.error(f"Error opening Smart Irrigation Control valve {self._attr_name}: {e}")
            raise

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"Closing Smart Irrigation Control valve {self._attr_name} ({self.valve_service.id})")
        if not self.valve_service:
            _LOGGER.error(f"No valve service available for Smart Irrigation Control valve {self._attr_name}")
            return
        command_data = {
            "data": {
                "id": "close_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "STOP_UNTIL_NEXT_TASK",
                },
            }
        }
        try:
            await self._async_send_valve_command(command_data, "closing")
        except Exception as e:
            _LOGGER.error(f"Error closing Smart Irrigation Control valve {self._attr_name}: {e}")
            raise


class GardenaValve(_GardenaValveBase):
    """Representation of a generic Gardena valve."""

    _log_label = "Valve"

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the valve."""
        super().__init__(coordinator, device, valve_service)
        self._attr_name = valve_service.name
        self._attr_unique_id = f"{device.id}_{valve_service.id}"

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info(f"Opening valve {self.valve_service.name} ({self.valve_service.id})")
        if not self.valve_service:
            return
        seconds = self._get_configured_duration_seconds()
        command_data = {
            "data": {
                "id": "open_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "START_SECONDS_TO_OVERRIDE",
                    "seconds": seconds,
                },
            }
        }
        await self._async_send_valve_command(command_data, "opening")

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info(f"Closing valve {self.valve_service.name} ({self.valve_service.id})")
        if not self.valve_service:
            _LOGGER.error(f"No valve service available for {self.valve_service.name}")
            return
        command_data = {
            "data": {
                "id": "close_valve",
                "type": "VALVE_CONTROL",
                "attributes": {
                    "command": "STOP_UNTIL_NEXT_TASK",
                },
            }
        }
        try:
            await self._async_send_valve_command(command_data, "closing")
        except Exception as e:
            _LOGGER.error(f"Error closing valve {self.valve_service.name}: {e}")
            raise
