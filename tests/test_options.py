"""Tests for bridge option normalization."""

from __future__ import annotations

import unittest

from custom_components.ha_mqtt_device_bridge.const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
)
from custom_components.ha_mqtt_device_bridge.options import (
    BridgeOptions,
    parse_domain_csv,
)


class OptionsTest(unittest.TestCase):
    """Validate option parsing without Home Assistant dependencies."""

    def test_parse_domain_csv_normalizes_and_deduplicates(self) -> None:
        """Integration allowlist input is normalized."""
        self.assertEqual(
            parse_domain_csv(" Overkiz, miele,overkiz ,, "),
            ("overkiz", "miele"),
        )

    def test_bridge_options_from_mapping(self) -> None:
        """Config entry options are normalized for runtime use."""
        options = BridgeOptions.from_mapping(
            {
                CONF_TOPIC_PREFIX: "/ha2fhem/",
                CONF_QOS: "1",
                CONF_ALLOWED_INTEGRATIONS: "miele,overkiz",
            }
        )

        self.assertEqual(options.topic_prefix, "ha2fhem")
        self.assertEqual(options.qos, 1)
        self.assertEqual(options.allowed_integrations, ("miele", "overkiz"))


if __name__ == "__main__":
    unittest.main()

