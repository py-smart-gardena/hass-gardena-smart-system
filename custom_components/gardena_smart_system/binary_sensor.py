"""Support for Gardena Smart System websocket connection status."""
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)

from custom_components.gardena_smart_system import GARDENA_SYSTEM
from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Gardena websocket connection status."""
    async_add_entities([SmartSystemWebsocketStatus(hass.data[DOMAIN][GARDENA_SYSTEM])], True)


class SmartSystemWebsocketStatus(BinarySensorEntity):
    """Representation of an InComfort Failed sensor."""

    def __init__(self, smart_system) -> None:
        """Initialize the binary sensor."""
        super().__init__()
        self._unique_id = "smart_gardena_websocket_status"
        self._name = "Gardena Smart System connection"
        self._smart_system = smart_system

    @property
    def is_on(self) -> bool:
        """Return the status of the sensor."""
        return self._smart_system.ws_status == "ONLINE"

    @property
    def should_poll(self) -> bool:
        """No polling needed for a sensor."""
        return False

    def update_callback(self, device):
        """Call update for Home Assistant when the device is updated."""
        self.schedule_update_ha_state(True)
