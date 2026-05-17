"""Config flow for Gardena Smart System integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .coordinator import (
    OPT_PUSH_MODE,
    OPT_WEBHOOK_EXTERNAL_URL,
    PUSH_MODE_WEBHOOK,
    PUSH_MODE_WEBSOCKET,
)
from .gardena_client import GardenaAPIError, GardenaSmartSystemClient
from .auth import GardenaAuthError

_LOGGER = logging.getLogger(__name__)


class GardenaSmartSystemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gardena Smart System."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "GardenaOptionsFlowHandler":
        """Get the options flow for this handler.

        Note: do NOT pass `config_entry` to the handler constructor. HA injects
        it as a read-only property on the OptionsFlow base class. Passing it
        and storing it as `self.config_entry = ...` raises AttributeError on
        HA 2024.12+.
        """
        return GardenaOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                _LOGGER.info("Testing Gardena Smart System credentials")

                # Test the credentials
                import os
                dev_mode = os.getenv('GARDENA_DEV_MODE', 'false').lower() == 'true'
                client = GardenaSmartSystemClient(
                    client_id=user_input[CONF_CLIENT_ID],
                    client_secret=user_input[CONF_CLIENT_SECRET],
                    dev_mode=dev_mode,  # Enable dev mode for SSL issues on macOS
                )

                # Try to authenticate and get locations
                locations = await client.get_locations()

                if not locations:
                    _LOGGER.warning("No locations found for the provided credentials")
                    errors["base"] = "no_locations"
                else:
                    _LOGGER.info("Successfully authenticated and found %d locations", len(locations))

                    # If we get here, the credentials are valid
                    return self.async_create_entry(
                        title="Gardena Smart System",
                        data=user_input,
                    )

            except GardenaAuthError as ex:
                _LOGGER.error("Authentication failed: %s", ex)
                errors["base"] = "invalid_auth"
            except GardenaAPIError as ex:
                _LOGGER.error("API error during configuration: %s (status: %s)", ex, ex.status_code)
                if ex.status_code == 404:
                    errors["base"] = "no_locations"
                else:
                    errors["base"] = "api_error"
            except Exception as ex:
                _LOGGER.error("Unexpected error during configuration: %s", ex)
                errors["base"] = "unknown"

            finally:
                # Always close the client
                try:
                    await client.close()
                except Exception as ex:
                    _LOGGER.warning("Error closing client: %s", ex)

        # Show the form
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


class GardenaOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow: choose push transport (WebSocket vs Webhook).

    HA 2024.12+ exposes `self.config_entry` as a read-only property that the
    framework sets automatically — we must NOT assign it ourselves (raises
    AttributeError: 'property has no setter').
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    OPT_PUSH_MODE,
                    default=current.get(OPT_PUSH_MODE, PUSH_MODE_WEBSOCKET),
                ): vol.In([PUSH_MODE_WEBSOCKET, PUSH_MODE_WEBHOOK]),
                vol.Optional(
                    OPT_WEBHOOK_EXTERNAL_URL,
                    default=current.get(OPT_WEBHOOK_EXTERNAL_URL, ""),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
