"""Tests for FHEM rendering helpers."""

from __future__ import annotations

import unittest

from custom_components.ha_mqtt_device_bridge.fhem import (
    FhemDeviceConfig,
    FhemSetCommand,
)
from custom_components.ha_mqtt_device_bridge.slug import ascii_slug, fhem_device_name


class SlugHelperTest(unittest.TestCase):
    """Validate deterministic slug and FHEM name generation."""

    def test_ascii_slug_normalizes_names(self) -> None:
        """Names are converted to stable MQTT path segments."""
        self.assertEqual(ascii_slug("Miele Waschmaschine"), "miele_waschmaschine")
        self.assertEqual(ascii_slug("Store - Küche links"), "store_kuche_links")
        self.assertEqual(ascii_slug("***", fallback="fallback"), "fallback")

    def test_fhem_device_name_is_stable_and_prefixed(self) -> None:
        """FHEM device names include a stable suffix to avoid collisions."""
        name = fhem_device_name("Miele Waschmaschine", "REDACTED_MIELE_DEVICE_ID")
        self.assertTrue(name.startswith("HA_Miele_Waschmaschine_"))
        self.assertEqual(name, fhem_device_name("Miele Waschmaschine", "REDACTED_MIELE_DEVICE_ID"))
        self.assertNotEqual(
            name,
            fhem_device_name("Miele Waschmaschine", "OTHER_DEVICE_ID"),
        )


class FhemRenderTest(unittest.TestCase):
    """Validate generated FHEM raw snippets."""

    def test_render_raw_config_with_setters(self) -> None:
        """A device config renders readingList, setList, setStateList, and webCmd."""
        config = FhemDeviceConfig(
            device_name="HA_Miele_Washer_ab12cd",
            cid="ha2fhem_miele_washer",
            availability_topic="ha2fhem/miele_washer/availability",
            readings_topic="ha2fhem/miele_washer/readings",
            set_commands=(
                FhemSetCommand(
                    name="power",
                    widget="on,off",
                    topic="ha2fhem/miele_washer/cmd/switch_power/set",
                    payload="$EVTPART1",
                ),
                FhemSetCommand(
                    name="start",
                    widget="noArg",
                    topic="ha2fhem/miele_washer/cmd/button_start/press",
                    payload="1",
                ),
            ),
            web_commands=("power", "start"),
            set_state_commands=("power:on,off",),
        )

        raw = config.render_raw()

        self.assertIn("defmod HA_Miele_Washer_ab12cd MQTT2_DEVICE ha2fhem_miele_washer", raw)
        self.assertIn("ha2fhem/miele_washer/readings:.* { json2nameValue($EVENT) }", raw)
        self.assertIn("power:on,off ha2fhem/miele_washer/cmd/switch_power/set $EVTPART1", raw)
        self.assertIn("start:noArg ha2fhem/miele_washer/cmd/button_start/press 1", raw)
        self.assertIn("attr HA_Miele_Washer_ab12cd setStateList power:on,off", raw)
        self.assertIn("attr HA_Miele_Washer_ab12cd webCmd power:start", raw)


if __name__ == "__main__":
    unittest.main()

