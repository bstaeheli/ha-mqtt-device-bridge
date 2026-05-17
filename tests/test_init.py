"""Integration tests for bridge setup, unload, and the republish service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_mqtt_device_bridge.const import DOMAIN, SERVICE_REPUBLISH


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading for all tests in this module."""


def _make_runtime_patch():
    """Return a patch context for MqttBridgeRuntime that needs no real MQTT."""
    mock_runtime = MagicMock()
    mock_runtime.async_setup = AsyncMock()
    mock_runtime.async_unload = AsyncMock()
    mock_runtime.async_republish = AsyncMock()
    mock_runtime.diagnostics_data = MagicMock(return_value={"published_device_count": 0})
    return patch(
        "custom_components.ha_mqtt_device_bridge.MqttBridgeRuntime",
        return_value=mock_runtime,
    ), mock_runtime


async def test_setup_entry_creates_runtime(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_setup_entry wires up the runtime and marks the entry loaded."""
    mock_config_entry.add_to_hass(hass)

    patch_mqtt = patch(
        "homeassistant.components.mqtt.async_wait_for_mqtt_client",
        return_value=None,
    )
    runtime_patch, mock_runtime = _make_runtime_patch()

    with patch_mqtt, runtime_patch:
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    mock_runtime.async_setup.assert_awaited_once()


async def test_unload_entry_calls_runtime_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_unload_entry tears down MQTT subscriptions via the runtime."""
    mock_config_entry.add_to_hass(hass)

    patch_mqtt = patch(
        "homeassistant.components.mqtt.async_wait_for_mqtt_client",
        return_value=None,
    )
    runtime_patch, mock_runtime = _make_runtime_patch()

    with patch_mqtt, runtime_patch:
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    mock_runtime.async_unload.assert_awaited_once()


async def test_republish_service_triggers_runtime(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The republish service action forwards to the loaded runtime."""
    mock_config_entry.add_to_hass(hass)

    patch_mqtt = patch(
        "homeassistant.components.mqtt.async_wait_for_mqtt_client",
        return_value=None,
    )
    runtime_patch, mock_runtime = _make_runtime_patch()

    with patch_mqtt, runtime_patch:
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPUBLISH,
            {},
            blocking=True,
        )

    mock_runtime.async_republish.assert_awaited()
