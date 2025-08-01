"""Tests for the Gardena Smart System integration."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import DOMAIN


@pytest.fixture
def mock_gardena_client():
    """Mock Gardena Smart System client."""
    with patch("custom_components.gardena_smart_system.gardena_client.GardenaSmartSystemClient") as mock:
        client = mock.return_value
        client.get_locations = AsyncMock(return_value=[
            {
                "id": "test-location-id",
                "type": "LOCATION",
                "attributes": {"name": "Test Garden"}
            }
        ])
        client.get_location = AsyncMock(return_value={
            "data": {
                "id": "test-location-id",
                "type": "LOCATION",
                "attributes": {"name": "Test Garden"}
            },
            "included": [
                {
                    "id": "test-device-id",
                    "type": "DEVICE",
                    "attributes": {
                        "name": {"value": "Test Mower"},
                        "modelType": {"value": "Test Model"},
                        "serial": {"value": "12345"}
                    }
                },
                {
                    "id": "test-mower-service-id",
                    "type": "MOWER",
                    "attributes": {
                        "state": {"value": "OK"},
                        "activity": {"value": "OK_CUTTING"}
                    },
                    "relationships": {
                        "device": {
                            "data": {"id": "test-device-id"}
                        }
                    }
                }
            ]
        })
        yield client


async def test_config_flow_success(hass: HomeAssistant, mock_gardena_client) -> None:
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CLIENT_ID: "test-client-id",
            CONF_CLIENT_SECRET: "test-client-secret",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Gardena Smart System"
    assert result["data"] == {
        CONF_CLIENT_ID: "test-client-id",
        CONF_CLIENT_SECRET: "test-client-secret",
    }


async def test_config_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test config flow with invalid authentication."""
    with patch("custom_components.gardena_smart_system.gardena_client.GardenaSmartSystemClient") as mock:
        client = mock.return_value
        client.get_locations = AsyncMock(side_effect=Exception("Authentication failed"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "invalid-client-id",
                CONF_CLIENT_SECRET: "invalid-client-secret",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"


async def test_setup_entry(hass: HomeAssistant, mock_gardena_client) -> None:
    """Test setting up the integration."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_CLIENT_ID: "test-client-id",
        CONF_CLIENT_SECRET: "test-client-secret",
    }
    config_entry.entry_id = "test-entry-id"

    with patch("custom_components.gardena_smart_system.async_setup_entry", return_value=True):
        result = await hass.config_entries.async_setup(config_entry.entry_id)
        assert result is True


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading the integration."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry-id"

    with patch("custom_components.gardena_smart_system.async_unload_entry", return_value=True):
        result = await hass.config_entries.async_unload(config_entry.entry_id)
        assert result is True 