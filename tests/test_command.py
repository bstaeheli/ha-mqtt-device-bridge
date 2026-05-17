"""Tests for MQTT command to Home Assistant service-call mapping."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from custom_components.ha_mqtt_device_bridge.command import (
    CommandError,
    build_command_definitions,
    service_call_for_command,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"


def load_fixture(name: str):
    """Load an example fixture."""
    with (EXAMPLES / name).open(encoding="utf-8") as file:
        return json.load(file)


class CommandMappingTest(unittest.TestCase):
    """Validate command mapping against fixture exports."""

    def test_builds_allowed_topics_from_overkiz_fixture(self) -> None:
        """Overkiz cover, button, and number entities produce command topics."""
        export = load_fixture("overkiz-template-export.json")

        definitions = build_command_definitions(export)

        self.assertIn(
            "ha2fhem/overkiz_fixture_device/cmd/cover_overkiz_fixture_2/open",
            definitions,
        )
        self.assertIn(
            "ha2fhem/overkiz_fixture_device/cmd/cover_overkiz_fixture_2/position",
            definitions,
        )
        self.assertIn(
            "ha2fhem/overkiz_fixture_device/cmd/number_overkiz_fixture_3/set",
            definitions,
        )
        self.assertNotIn(
            "ha2fhem/overkiz_fixture_device/cmd/cover_overkiz_fixture_2/delete",
            definitions,
        )

    def test_builds_switch_topic_from_miele_fixture(self) -> None:
        """The Miele fixture exposes only its switch as actionable."""
        export = load_fixture("miele-template-export.json")

        definitions = build_command_definitions(export)

        self.assertEqual(set(definitions), {
            "ha2fhem/miele_fixture_appliance/cmd/switch_miele_fixture_17/set"
        })

    def test_maps_switch_payload_to_turn_on_off(self) -> None:
        """Switch scalar payloads map to HA switch services."""
        on = service_call_for_command(
            entity_id="switch.miele_fixture_17",
            domain="switch",
            command="set",
            payload="on",
        )
        off = service_call_for_command(
            entity_id="switch.miele_fixture_17",
            domain="switch",
            command="set",
            payload="off",
        )

        self.assertEqual(on.service, "turn_on")
        self.assertEqual(on.service_data, {"entity_id": "switch.miele_fixture_17"})
        self.assertEqual(off.service, "turn_off")

    def test_maps_additional_domain_payloads(self) -> None:
        """Common action domains map to the expected HA services."""
        light = service_call_for_command(
            entity_id="light.kitchen",
            domain="light",
            command="set",
            payload="toggle",
        )
        lock = service_call_for_command(
            entity_id="lock.front_door",
            domain="lock",
            command="set",
            payload="unlock",
        )
        scene = service_call_for_command(
            entity_id="scene.evening",
            domain="scene",
            command="turn_on",
            payload="1",
        )
        siren = service_call_for_command(
            entity_id="siren.alarm",
            domain="siren",
            command="set",
            payload="on",
        )

        self.assertEqual(light.service, "toggle")
        self.assertEqual(lock.service, "unlock")
        self.assertEqual(scene.service, "turn_on")
        self.assertEqual(siren.service, "turn_on")

    def test_maps_cover_position_to_integer_percentage(self) -> None:
        """Cover position commands require an integer percentage."""
        call = service_call_for_command(
            entity_id="cover.overkiz_fixture_2",
            domain="cover",
            command="position",
            payload="42",
        )

        self.assertEqual(call.domain, "cover")
        self.assertEqual(call.service, "set_cover_position")
        self.assertEqual(
            call.service_data,
            {"entity_id": "cover.overkiz_fixture_2", "position": 42},
        )

    def test_rejects_invalid_payloads(self) -> None:
        """Invalid scalar payloads are rejected before HA service calls."""
        with self.assertRaises(CommandError):
            service_call_for_command(
                entity_id="switch.miele_fixture_17",
                domain="switch",
                command="set",
                payload="maybe",
            )

        with self.assertRaises(CommandError):
            service_call_for_command(
                entity_id="cover.overkiz_fixture_2",
                domain="cover",
                command="position",
                payload="101",
            )

        with self.assertRaises(CommandError):
            service_call_for_command(
                entity_id="light.kitchen",
                domain="light",
                command="set",
                payload="dim",
            )


if __name__ == "__main__":
    unittest.main()
