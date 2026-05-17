"""Integration tests for the runtime MQTT publish behaviour."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from homeassistant.core import HomeAssistant
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


def _sample_export(topic_prefix: str = "ha2fhem") -> dict:
    """Minimal template export for a single switch entity."""
    return {
        "export_version": 1,
        "root_entity": "switch.test_switch",
        "device_id": "test-device-id",
        "device": {
            "name": "Test Device",
            "name_by_user": None,
            "manufacturer": None,
            "model": None,
            "model_id": None,
            "sw_version": None,
            "hw_version": None,
            "integration_domains": ["test_integration"],
        },
        "entities": [
            {
                "entity_id": "switch.test_switch",
                "domain": "switch",
                "friendly_name": "Test Switch",
                "state": "off",
                "attributes": {},
                "config_entry_id": "cfg-1",
                "config_entry_domain": "test_integration",
                "config_entry_title": "Test",
            }
        ],
    }


async def test_setup_publishes_four_retained_topics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """On setup, availability, readings, meta, and fhem/raw are published."""
    mock_config_entry.add_to_hass(hass)

    published: list[tuple] = []

    async def _fake_publish(hass_, topic, payload, qos, retain):
        published.append((topic, payload, qos, retain))

    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch("homeassistant.components.mqtt.async_publish", side_effect=_fake_publish),
        patch(
            "homeassistant.components.mqtt.async_subscribe",
            return_value=lambda: None,
        ),
        patch(
            "custom_components.ha_mqtt_device_bridge.runtime.collect_device_template_exports",
            return_value=[_sample_export()],
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    topics = [t for t, *_ in published]
    assert "ha2fhem/test_device/availability" in topics
    assert "ha2fhem/test_device/readings" in topics
    assert "ha2fhem/test_device/meta" in topics
    assert "ha2fhem/test_device/fhem/raw" in topics

    for topic, payload, qos, retain in published:
        assert retain is True, f"Topic {topic!r} must be retained"


async def test_unload_publishes_offline_availability(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Unloading the entry publishes 'offline' on the availability topic."""
    mock_config_entry.add_to_hass(hass)

    published: list[tuple] = []

    async def _fake_publish(hass_, topic, payload, qos, retain):
        published.append((topic, payload))

    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch("homeassistant.components.mqtt.async_publish", side_effect=_fake_publish),
        patch(
            "homeassistant.components.mqtt.async_subscribe",
            return_value=lambda: None,
        ),
        patch(
            "custom_components.ha_mqtt_device_bridge.runtime.collect_device_template_exports",
            return_value=[_sample_export()],
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        published.clear()

        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert ("ha2fhem/test_device/availability", "offline") in published


async def test_incoming_command_triggers_service_call(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An incoming MQTT command message is forwarded as a HA service call."""
    mock_config_entry.add_to_hass(hass)

    message_callback = None

    async def _fake_subscribe(hass_, topic_filter, callback, **kwargs):
        nonlocal message_callback
        message_callback = callback
        return lambda: None

    with (
        patch("homeassistant.components.mqtt.async_wait_for_mqtt_client"),
        patch("homeassistant.components.mqtt.async_publish", new_callable=AsyncMock),
        patch(
            "homeassistant.components.mqtt.async_subscribe",
            side_effect=_fake_subscribe,
        ),
        patch(
            "custom_components.ha_mqtt_device_bridge.runtime.collect_device_template_exports",
            return_value=[_sample_export()],
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert message_callback is not None

        # Spy on the runtime's own handler instead of patching the read-only ServiceRegistry.
        runtime = mock_config_entry.runtime_data.manager
        with patch.object(
            runtime, "async_handle_mqtt_message", new_callable=AsyncMock
        ) as mock_handle:
            class _FakeMsg:
                topic = "ha2fhem/test_device/cmd/switch_test_switch/set"
                payload = b"on"

            message_callback(_FakeMsg())
            await hass.async_block_till_done()

    mock_handle.assert_awaited_once_with(
        "ha2fhem/test_device/cmd/switch_test_switch/set", b"on"
    )
