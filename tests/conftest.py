"""Shared pytest fixtures for HA integration tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_mqtt_device_bridge.const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    DOMAIN,
)


@pytest.fixture
def bridge_options() -> dict[str, Any]:
    """Default bridge options for a test config entry."""
    return {
        CONF_TOPIC_PREFIX: "ha2fhem",
        CONF_QOS: 0,
        CONF_ALLOWED_INTEGRATIONS: ["overkiz", "miele"],
    }


@pytest.fixture
def mock_config_entry(bridge_options: dict[str, Any]) -> MockConfigEntry:
    """A minimal mock bridge config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Bridge",
        data={},
        options=bridge_options,
        unique_id=DOMAIN,
    )
