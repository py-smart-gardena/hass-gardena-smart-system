"""Config flow for Gardena Smart System integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_MOW_NOW_DURATION,
    CONF_START_MOWING_BEHAVIOR,
    DEFAULT_MOW_NOW_DURATION,
    DOMAIN,
    START_MOWING_MOW_NOW,
    START_MOWING_RESUME_SCHEDULE,
)
from .credential_validation import async_validate_gardena_credentials

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gardena Smart System."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return GardenaOptionsFlowHandler()

    def _credentials_schema(self) -> vol.Schema:
        """Schema for API credential input."""
        return vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
            }
        )

    async def _apply_credential_updates(
        self,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, Any],
    ) -> FlowResult:
        """Persist credentials; reload only when the config entry is enabled."""
        self.hass.config_entries.async_update_entry(
            entry,
            data={
                CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
            },
        )
        if entry.disabled_by is None:
            await self.hass.config_entries.async_reload(entry.entry_id)
        else:
            _LOGGER.info(
                "Credentials updated for disabled config entry %s; "
                "enable the integration to connect",
                entry.entry_id,
            )
        return self.async_abort(reason="reconfigure_successful")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await async_validate_gardena_credentials(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Gardena Smart System",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._credentials_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow updating API credentials without removing the config entry."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await async_validate_gardena_credentials(user_input)
            if not errors:
                return await self._apply_credential_updates(
                    reconfigure_entry, user_input
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                self._credentials_schema(),
                {
                    CONF_CLIENT_ID: reconfigure_entry.data.get(CONF_CLIENT_ID, ""),
                    CONF_CLIENT_SECRET: reconfigure_entry.data.get(
                        CONF_CLIENT_SECRET, ""
                    ),
                },
            ),
            errors=errors,
        )


class GardenaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Gardena Smart System options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose what the lawn mower Start button does (#399)."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_START_MOWING_BEHAVIOR): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    START_MOWING_RESUME_SCHEDULE,
                                    START_MOWING_MOW_NOW,
                                ],
                                translation_key="start_mowing_behavior",
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(CONF_MOW_NOW_DURATION): NumberSelector(
                            NumberSelectorConfig(
                                min=60,
                                max=86400,
                                step=60,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
                {
                    CONF_START_MOWING_BEHAVIOR: options.get(
                        CONF_START_MOWING_BEHAVIOR, START_MOWING_RESUME_SCHEDULE
                    ),
                    CONF_MOW_NOW_DURATION: options.get(
                        CONF_MOW_NOW_DURATION, DEFAULT_MOW_NOW_DURATION
                    ),
                },
            ),
        )
