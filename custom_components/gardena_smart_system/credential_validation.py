"""Shared credential validation for config flow."""
from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET

from .auth import GardenaAuthError
from .gardena_client import GardenaAPIError, GardenaSmartSystemClient

_LOGGER = logging.getLogger(__name__)


def _dev_mode_enabled() -> bool:
    """Return whether development mode is enabled."""
    return os.getenv("GARDENA_DEV_MODE", "false").lower() == "true"


async def async_validate_gardena_credentials(
    user_input: dict[str, Any],
) -> dict[str, str]:
    """Validate credentials against the Gardena API. Returns error dict (may be empty)."""
    errors: dict[str, str] = {}
    client: GardenaSmartSystemClient | None = None

    try:
        _LOGGER.info("Testing Gardena Smart System credentials")
        client = GardenaSmartSystemClient(
            client_id=user_input[CONF_CLIENT_ID],
            client_secret=user_input[CONF_CLIENT_SECRET],
            dev_mode=_dev_mode_enabled(),
        )
        locations = await client.get_locations()
        if not locations:
            _LOGGER.warning("No locations found for the provided credentials")
            errors["base"] = "no_locations"
        else:
            _LOGGER.info(
                "Successfully authenticated and found %d locations", len(locations)
            )
    except GardenaAuthError as ex:
        _LOGGER.error("Authentication failed: %s", ex)
        errors["base"] = "invalid_auth"
    except GardenaAPIError as ex:
        _LOGGER.error(
            "API error during configuration: %s (status: %s)", ex, ex.status_code
        )
        if ex.status_code == 429:
            errors["base"] = "too_many_requests"
        elif ex.status_code == 404:
            errors["base"] = "no_locations"
        else:
            errors["base"] = "api_error"
    except Exception as ex:
        _LOGGER.error("Unexpected error during configuration: %s", ex)
        errors["base"] = "unknown"
    finally:
        if client is not None:
            try:
                await client.close()
            except Exception as ex:
                _LOGGER.warning("Error closing client: %s", ex)

    return errors
