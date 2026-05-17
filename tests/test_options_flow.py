"""Integration tests for the bridge options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_mqtt_device_bridge.const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_RETAIN,
    CONF_TOPIC_PREFIX,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading for all tests in this module."""


def _mock_runtime():
    """Minimal mock runtime that does nothing."""
    rt = MagicMock()
    rt.async_setup = AsyncMock()
    rt.async_unload = AsyncMock()
    rt.async_republish = AsyncMock()
    return rt


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add entry to hass and load it with a mocked runtime."""
    entry.add_to_hass(hass)
    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch(
            "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
            return_value=_mock_runtime(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_options_flow_shows_current_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Options flow init step shows a form with current option values."""
    await _setup_entry(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONF_TOPIC_PREFIX in schema_keys
    assert CONF_QOS in schema_keys
    assert CONF_RETAIN in schema_keys
    assert CONF_ALLOWED_INTEGRATIONS in schema_keys


async def test_options_flow_saves_updated_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Submitting the options form saves the new values to the config entry."""
    await _setup_entry(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch(
            "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
            return_value=_mock_runtime(),
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_TOPIC_PREFIX: "newprefix",
                CONF_QOS: 1,
                CONF_RETAIN: False,
                CONF_ALLOWED_INTEGRATIONS: "overkiz,miele",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_TOPIC_PREFIX] == "newprefix"
    assert mock_config_entry.options[CONF_QOS] == 1
    assert mock_config_entry.options[CONF_RETAIN] is False
    assert mock_config_entry.options[CONF_ALLOWED_INTEGRATIONS] == ["overkiz", "miele"]


async def test_options_flow_normalizes_allowed_integrations(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Allowed integrations are lowercased, deduplicated, and stripped."""
    await _setup_entry(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch(
            "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
            return_value=_mock_runtime(),
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_TOPIC_PREFIX: "ha2fhem",
                CONF_QOS: 0,
                CONF_RETAIN: True,
                CONF_ALLOWED_INTEGRATIONS: " Overkiz , MIELE , overkiz ",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_ALLOWED_INTEGRATIONS] == ["overkiz", "miele"]
