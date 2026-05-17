"""Integration tests for bridge diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_mqtt_device_bridge.const import DOMAIN


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading for all tests in this module."""


async def test_diagnostics_returns_expected_keys(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics payload includes domain, entry, and runtime sections."""
    from custom_components.ha_mqtt_device_bridge.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_config_entry.add_to_hass(hass)

    mock_runtime = MagicMock()
    mock_runtime.async_setup = AsyncMock()
    mock_runtime.async_unload = AsyncMock()
    mock_runtime.async_republish = AsyncMock()
    mock_runtime.diagnostics_data = MagicMock(
        return_value={
            "published_device_count": 2,
            "command_topic_count": 5,
            "topic_prefix": "ha2fhem",
            "qos": 0,
            "allowed_integrations": ("overkiz", "miele"),
            "devices": [],
        }
    )

    with (
        patch(
            "homeassistant.components.mqtt.async_wait_for_mqtt_client",
            return_value=None,
        ),
        patch(
            "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
            return_value=mock_runtime,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        diag = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diag["domain"] == DOMAIN
    assert "entry" in diag
    assert "runtime" in diag
    assert diag["runtime"]["published_device_count"] == 2


async def test_diagnostics_redacts_sensitive_fields(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics redacts device_id, entity_id, and config_entry_id."""
    from custom_components.ha_mqtt_device_bridge.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_runtime = MagicMock()
    mock_runtime.async_setup = AsyncMock()
    mock_runtime.async_unload = AsyncMock()
    mock_runtime.async_republish = AsyncMock()
    mock_runtime.diagnostics_data = MagicMock(
        return_value={
            "published_device_count": 1,
            "command_topic_count": 1,
            "topic_prefix": "ha2fhem",
            "qos": 0,
            "allowed_integrations": ("overkiz",),
            "devices": [
                {
                    "device_id": "secret-device-id",
                    "name": "My Cover",
                    "entity_count": 1,
                    "entities": [
                        {
                            "entity_id": "cover.my_cover",
                            "domain": "cover",
                        }
                    ],
                }
            ],
        }
    )

    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.mqtt.async_wait_for_mqtt_client",
            return_value=None,
        ),
        patch(
            "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
            return_value=mock_runtime,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        diag = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    import json

    dumped = json.dumps(diag)
    assert "secret-device-id" not in dumped
    assert "cover.my_cover" not in dumped
