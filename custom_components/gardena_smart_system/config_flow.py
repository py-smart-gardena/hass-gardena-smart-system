"""Config flow for Gardena Smart System integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .gardena_client import GardenaSmartSystemClient, GardenaAPIError
from .auth import GardenaAuthError

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
                _LOGGER.info("Testing Gardena Smart System credentials")
                
                # Test the credentials
                client = GardenaSmartSystemClient(
                    client_id=user_input[CONF_CLIENT_ID],
                    client_secret=user_input[CONF_CLIENT_SECRET],
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
                _LOGGER.error("Authentication failed: %s (status: %s)", ex, ex.status_code)
                if ex.status_code == 401:
                    errors["base"] = "invalid_auth"
                elif ex.status_code == 403:
                    errors["base"] = "insufficient_permissions"
                else:
                    errors["base"] = "auth_error"
                    
            except GardenaAPIError as ex:
                _LOGGER.error("API error during configuration: %s (status: %s)", ex, ex.status_code)
                if ex.status_code == 401:
                    errors["base"] = "invalid_auth"
                elif ex.status_code == 403:
                    errors["base"] = "insufficient_permissions"
                elif ex.status_code == 404:
                    errors["base"] = "no_locations"
                elif ex.status_code in (500, 502):
                    errors["base"] = "server_error"
                else:
                    errors["base"] = "unknown_error"
                    
            except Exception as ex:
                _LOGGER.error("Unexpected error during configuration: %s", ex, exc_info=True)
                errors["base"] = "unknown_error"
            finally:
                # Clean up the test client
                try:
                    await client.close()
                except Exception:
                    pass

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