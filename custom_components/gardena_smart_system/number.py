"""Support for Gardena Smart System number entities (watering duration)."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_VALVE_DURATIONS
from .coordinator import GardenaSmartSystemCoordinator
from .entities import GardenaEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_DURATION_MINUTES = 60
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 1440


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gardena Smart System number entities."""
    coordinator: GardenaSmartSystemCoordinator = hass.data[DOMAIN][entry.entry_id]

    if CONF_VALVE_DURATIONS not in hass.data[DOMAIN]:
        hass.data[DOMAIN][CONF_VALVE_DURATIONS] = {}

    entities = []

    for location in coordinator.locations.values():
        for device in location.devices.values():
            if "VALVE" in device.services:
                valve_services = device.services["VALVE"]
                for valve_service in valve_services:
                    entities.append(
                        GardenaValveDurationNumber(coordinator, device, valve_service)
                    )

    async_add_entities(entities)


class GardenaValveDurationNumber(GardenaEntity, NumberEntity, RestoreEntity):
    """Number entity to configure watering duration for a valve."""

    def __init__(self, coordinator: GardenaSmartSystemCoordinator, device, valve_service) -> None:
        """Initialize the valve duration number."""
        super().__init__(coordinator, device, "VALVE")
        self._valve_service = valve_service
        self._device_id = device.id
        self._name_per_valve("watering_duration", valve_service)
        self._keep_entity_id(
            "number",
            f"{device.name} {valve_service.name} Watering Duration"
            if valve_service.name
            else f"{device.name} Watering Duration",
        )
        self._attr_unique_id = f"{device.id}_{valve_service.id}_watering_duration"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_native_min_value = MIN_DURATION_MINUTES
        self._attr_native_max_value = MAX_DURATION_MINUTES
        self._attr_native_step = 1
        self._attr_mode = NumberMode.BOX
        self._attr_icon = "mdi:timer-outline"
        self._duration_minutes: float = DEFAULT_DURATION_MINUTES

    async def async_added_to_hass(self) -> None:
        """Restore last known value on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._duration_minutes = float(last_state.state)
        self.hass.data[DOMAIN][CONF_VALVE_DURATIONS][self._valve_service.id] = self._duration_minutes

    @property
    def native_value(self) -> float:
        """Return the current configured duration in minutes."""
        return self._duration_minutes

    async def async_set_native_value(self, value: float) -> None:
        """Set the watering duration in minutes."""
        self._duration_minutes = value
        self.hass.data[DOMAIN][CONF_VALVE_DURATIONS][self._valve_service.id] = value
        self.async_write_ha_state()
