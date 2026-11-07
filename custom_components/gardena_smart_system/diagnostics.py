"""Diagnostics for Gardena Smart System (#408).

What Settings › Devices & services › Gardena › Download diagnostics gives:
the config entry, the devices and services as the API and the WebSocket
reported them, the WebSocket's connection state and the API usage. Anything
that identifies the account or a device is redacted.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

# Keys redacted wherever they appear: the credentials, the serial numbers of
# devices, and the WebSocket URL, which carries a session token.
TO_REDACT = {
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    "access_token",
    "refresh_token",
    "serial",
    "websocket_url",
}


def _as_dict(value: Any) -> Any:
    """A model as plain data; anything else as it is."""
    return asdict(value) if is_dataclass(value) else value


def _locations(coordinator) -> list[dict[str, Any]]:
    """The locations with their devices and services, the garden name redacted."""
    locations = []
    for location in (getattr(coordinator, "locations", None) or {}).values():
        devices = [_as_dict(device) for device in (location.devices or {}).values()]
        locations.append(
            {
                "id": location.id,
                # The garden name is the user's own: often a family or street name.
                "name": REDACTED,
                "devices": devices,
            }
        )
    return locations


def _websocket(coordinator) -> dict[str, Any] | None:
    """The WebSocket's connection state, without its URL."""
    client = getattr(coordinator, "websocket_client", None)
    if client is None:
        return None
    return {
        "status": getattr(client, "connection_status", None),
        "is_connected": getattr(client, "is_connected", None),
        "is_connecting": getattr(client, "is_connecting", None),
        "reconnect_attempts": getattr(client, "reconnect_attempts", None),
    }


def _api_usage(coordinator) -> dict[str, Any] | None:
    """Requests made against the weekly quota."""
    tracker = getattr(getattr(coordinator, "client", None), "api_tracker", None)
    if tracker is None:
        return None
    return {
        "requests_this_week": tracker.requests_this_week,
        "requests_today": tracker.requests_today,
        "total_requests": tracker.total_requests,
        "requests_by_endpoint": tracker.requests_by_endpoint(),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    diagnostics: dict[str, Any] = {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
    }
    if coordinator is not None:
        diagnostics["coordinator"] = {
            "last_update_success": getattr(coordinator, "last_update_success", None),
        }
        diagnostics["websocket"] = _websocket(coordinator)
        diagnostics["api_usage"] = _api_usage(coordinator)
        diagnostics["locations"] = _locations(coordinator)
    return async_redact_data(diagnostics, TO_REDACT)
