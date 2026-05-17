"""Tests for config flow importability without Home Assistant deps."""

from __future__ import annotations

import unittest


class ConfigFlowImportTest(unittest.TestCase):
    """Ensure the config flow module remains importable in local tests."""

    def test_config_flow_module_imports_without_homeassistant(self) -> None:
        """The module should load even when Home Assistant is unavailable."""
        from custom_components.ha_mqtt_device_bridge import config_flow

        self.assertEqual(config_flow.CONF_NAME, "name")
        self.assertTrue(hasattr(config_flow, "HaMqttDeviceBridgeConfigFlow"))


if __name__ == "__main__":
    unittest.main()
