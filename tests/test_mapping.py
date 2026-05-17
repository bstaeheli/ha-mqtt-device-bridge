"""Tests for mapping fixture exports to FHEM artifacts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from custom_components.ha_mqtt_device_bridge.mapping import (
    build_fhem_device_config,
    build_readings_payload,
    entity_slug,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"


def load_fixture(name: str):
    """Load an example fixture."""
    with (EXAMPLES / name).open(encoding="utf-8") as file:
        return json.load(file)


class MappingTest(unittest.TestCase):
    """Validate mapping behavior against real redacted exports."""

    def test_entity_slug_keeps_domain_context(self) -> None:
        """Command slugs include the HA domain to avoid collisions."""
        self.assertEqual(
            entity_slug("cover.overkiz_fixture_2"),
            "cover_overkiz_fixture_2",
        )

    def test_overkiz_fixture_builds_cover_number_and_button_commands(self) -> None:
        """The Overkiz fixture generates actionable FHEM setters."""
        export = load_fixture("overkiz-template-export.json")

        config = build_fhem_device_config(export)
        raw = config.render_raw()
        command_names = {command.name for command in config.set_commands}

        self.assertTrue(config.device_name.startswith("HA_Overkiz_Fixture_Device_"))
        self.assertEqual(config.readings_topic, "ha2fhem/overkiz_fixture_device/readings")
        self.assertIn("overkiz_fixture_0", command_names)
        self.assertIn("overkiz_fixture_1", command_names)
        self.assertIn("overkiz_fixture_2_open", command_names)
        self.assertIn("overkiz_fixture_2_position", command_names)
        self.assertIn("overkiz_fixture_3", command_names)
        self.assertIn(
            "ha2fhem/overkiz_fixture_device/cmd/cover_overkiz_fixture_2/open",
            raw,
        )
        self.assertIn(
            "overkiz_fixture_3:slider,0,1,100",
            raw,
        )

    def test_miele_fixture_builds_switch_command_only(self) -> None:
        """The Miele fixture exposes the switch and keeps sensors read-only."""
        export = load_fixture("miele-template-export.json")

        config = build_fhem_device_config(export)

        self.assertTrue(config.device_name.startswith("HA_Miele_Fixture_Appliance_"))
        self.assertEqual(config.readings_topic, "ha2fhem/miele_fixture_appliance/readings")
        self.assertEqual(len(config.set_commands), 1)
        self.assertEqual(config.set_commands[0].name, "miele_fixture_17")
        self.assertEqual(config.set_commands[0].widget, "on,off")

    def test_readings_payload_contains_entity_state_and_cover_positions(self) -> None:
        """Readings payload keeps state data compact and FHEM-friendly."""
        export = load_fixture("overkiz-template-export.json")

        payload = build_readings_payload(export)

        self.assertEqual(payload["overkiz_fixture_2"], "closed")
        self.assertEqual(payload["overkiz_fixture_2_position"], 0)
        self.assertEqual(payload["overkiz_fixture_2_tilt_position"], 0)
        self.assertEqual(payload["overkiz_fixture_3"], "97")


if __name__ == "__main__":
    unittest.main()

