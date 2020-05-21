"""Config flow for Gardena integration."""
from collections import OrderedDict
import logging

from gardena.smart_system import SmartSystem

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_EMAIL, CONF_PASSWORD

from .const import (
    DOMAIN,
    CONF_APPLICATION_KEY,
    CONF_MOWER_DURATION,
    CONF_SMART_IRRIGATION_DURATION,
    CONF_SMART_WATERING_DURATION,
)


_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gardena."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        errors = {}

        fields = OrderedDict()
        fields[vol.Required(CONF_EMAIL)] = str
        fields[vol.Required(CONF_PASSWORD)] = str
        fields[vol.Required(CONF_APPLICATION_KEY)] = str

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return await self._show_setup_form()

        errors = {}
        try:
            await self.hass.async_add_executor_job(
                try_connection,
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                user_input[CONF_APPLICATION_KEY])
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
            return await self._show_setup_form(errors)

        unique_id = user_input[CONF_APPLICATION_KEY]

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=unique_id,
            data={
                CONF_ID: unique_id,
                CONF_EMAIL: user_input[CONF_EMAIL],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_APPLICATION_KEY: user_input[CONF_APPLICATION_KEY],

                # TODO: config options for these
                CONF_MOWER_DURATION: 60,
                CONF_SMART_IRRIGATION_DURATION: 60,
                CONF_SMART_WATERING_DURATION: 60,
            },
        )


def try_connection(email, password, application_key):
    _LOGGER.debug("Trying to connect to Gardena during setup")
    smart_system = SmartSystem(email=email, password=password, client_id=application_key)
    smart_system.authenticate()
    smart_system.update_locations()
    _LOGGER.debug("Successfully connected to Gardena during setup")
