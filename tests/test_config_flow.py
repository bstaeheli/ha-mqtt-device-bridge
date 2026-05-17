"""Integration tests for the bridge config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_mqtt_device_bridge.const import (
    CONF_QOS,
    CONF_RETAIN,
    CONF_TOPIC_PREFIX,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading for all tests in this module."""


async def test_config_flow_creates_entry(hass: HomeAssistant) -> None:
    """A complete user flow creates a loaded config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.ha_mqtt_device_bridge.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Test Bridge",
                CONF_TOPIC_PREFIX: "ha2fhem",
                CONF_QOS: 0,
                CONF_RETAIN: True,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Bridge"
    assert result["options"][CONF_TOPIC_PREFIX] == "ha2fhem"
    assert result["options"][CONF_QOS] == 0
    assert result["options"][CONF_RETAIN] is True


async def test_config_flow_aborts_if_already_configured(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """A second setup attempt for the same unique ID is rejected."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Bridge 2",
            CONF_TOPIC_PREFIX: "ha2fhem",
            CONF_QOS: 0,
            CONF_RETAIN: True,
        },
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
