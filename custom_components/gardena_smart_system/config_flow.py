"""Config flow for Gardena integration."""
import logging
from collections import OrderedDict

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from gardena.smart_system import SmartSystem
from homeassistant import config_entries
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ID,
)
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_MOWER_DURATION,
    CONF_SMART_IRRIGATION_DURATION,
    CONF_SMART_WATERING_DURATION,
    DEFAULT_MOWER_DURATION,
    DEFAULT_SMART_IRRIGATION_DURATION,
    DEFAULT_SMART_WATERING_DURATION,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPTIONS = {
    CONF_MOWER_DURATION: DEFAULT_MOWER_DURATION,
    CONF_SMART_IRRIGATION_DURATION: DEFAULT_SMART_IRRIGATION_DURATION,
    CONF_SMART_WATERING_DURATION: DEFAULT_SMART_WATERING_DURATION,
}


class GardenaSmartSystemConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gardena."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        errors = {}

        fields = OrderedDict()
        fields[vol.Required(CONF_CLIENT_ID)] = str
        fields[vol.Required(CONF_CLIENT_SECRET)] = str

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return await self._show_setup_form()

        errors = {}
        # try:
        #     await try_connection(
        #         user_input[CONF_CLIENT_ID],
        #         user_input[CONF_CLIENT_SECRET])
        # except Exception:  # pylint: disable=broad-except
        #     _LOGGER.exception("Unexpected exception")
        #     errors["base"] = "unknown"
        #     return await self._show_setup_form(errors)

        unique_id = user_input[CONF_CLIENT_ID]

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="",
            data={
                CONF_ID: unique_id,
                CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET]
            })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GardenaSmartSystemOptionsFlowHandler()


class GardenaSmartSystemOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self):
        """Initialize Gardena Smart System options flow."""
        super().__init__()

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            # TODO: Validate options (min, max values)
            return self.async_create_entry(title="", data=user_input)

        fields = OrderedDict()
        fields[vol.Optional(
            CONF_MOWER_DURATION,
            default=self.config_entry.options.get(
                CONF_MOWER_DURATION, DEFAULT_MOWER_DURATION))] = cv.positive_int
        fields[vol.Optional(
            CONF_SMART_IRRIGATION_DURATION,
            default=self.config_entry.options.get(
                CONF_SMART_IRRIGATION_DURATION, DEFAULT_SMART_IRRIGATION_DURATION))] = cv.positive_int
        fields[vol.Optional(
            CONF_SMART_WATERING_DURATION,
            default=self.config_entry.options.get(
                CONF_SMART_WATERING_DURATION, DEFAULT_SMART_WATERING_DURATION))] = cv.positive_int

        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields), errors=errors)


async def try_connection(client_id, client_secret):
    _LOGGER.debug("Trying to connect to Gardena during setup")
    smart_system = SmartSystem(client_id=client_id, client_secret=client_secret)
    await smart_system.authenticate()
    await smart_system.update_locations()
    await smart_system.quit()
    _LOGGER.debug("Successfully connected to Gardena during setup")
