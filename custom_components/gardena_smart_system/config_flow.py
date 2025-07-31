"""Config flow for Gardena Smart System integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .gardena_client import GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gardena Smart System."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Test the credentials
                client = GardenaSmartSystemClient(
                    client_id=user_input[CONF_CLIENT_ID],
                    client_secret=user_input[CONF_CLIENT_SECRET],
                )
                
                # Try to authenticate and get locations
                await client.get_locations()
                
                # If we get here, the credentials are valid
                return self.async_create_entry(
                    title="Gardena Smart System",
                    data=user_input,
                )
                
            except Exception as ex:
                _LOGGER.error("Failed to authenticate: %s", ex)
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                }
            ),
            errors=errors,
        ) 