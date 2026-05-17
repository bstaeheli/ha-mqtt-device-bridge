"""Regression tests for the redacted example exports."""

from __future__ import annotations

import json
import re
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"

TEMPLATE_FIXTURES = {
    "overkiz": {
        "path": EXAMPLES / "overkiz-template-export.json",
        "device_id": "REDACTED_OVERKIZ_DEVICE_ID",
        "root_entity": "cover.overkiz_fixture_2",
        "entity_count": 4,
        "domains": {"button", "cover", "number"},
        "entity_prefix": "overkiz_fixture_",
        "config_entry_id": "REDACTED_OVERKIZ_CONFIG_ENTRY_ID",
        "config_entry_title": "Overkiz Fixture",
    },
    "miele": {
        "path": EXAMPLES / "miele-template-export.json",
        "device_id": "REDACTED_MIELE_DEVICE_ID",
        "root_entity": "binary_sensor.miele_fixture_0",
        "entity_count": 18,
        "domains": {"binary_sensor", "sensor", "switch"},
        "entity_prefix": "miele_fixture_",
        "config_entry_id": "REDACTED_MIELE_CONFIG_ENTRY_ID",
        "config_entry_title": "Miele Fixture",
    },
}

DIAGNOSTIC_FIXTURES = {
    "overkiz": EXAMPLES / "overkiz-device-diagnostics.json",
    "miele": EXAMPLES / "miele-device-diagnostics.json",
}

SUSPICIOUS_VALUE = re.compile(
    r"("
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
    r"|eyJ[A-Za-z0-9_-]+"
    r"|bearer"
    r"|[0-9a-f]{24,}"
    r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r")",
    re.IGNORECASE,
)

SENSITIVE_KEY = re.compile(
    r"(token|secret|password|auth|serial|fabNumber|matNumber|swids|"
    r"gatewayId|deviceURL|subsystemId|controllableName|deviceName|server)",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    """Load a JSON fixture."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def iter_scalars(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Yield scalar values and their JSON paths."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_scalars(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_scalars(child, (*path, str(index)))
    else:
        yield path, value


class ExampleFixtureTest(unittest.TestCase):
    """Validate redacted examples used by implementation tests."""

    def test_template_exports_keep_expected_shape(self) -> None:
        """Template exports must remain useful as stable regression fixtures."""
        for integration, expected in TEMPLATE_FIXTURES.items():
            with self.subTest(integration=integration):
                data = load_json(expected["path"])

                self.assertEqual(data["export_version"], 1)
                self.assertEqual(data["device_id"], expected["device_id"])
                self.assertEqual(data["root_entity"], expected["root_entity"])
                self.assertEqual(len(data["entities"]), expected["entity_count"])
                self.assertEqual(
                    {entity["domain"] for entity in data["entities"]},
                    expected["domains"],
                )

                for index, entity in enumerate(data["entities"]):
                    domain = entity["domain"]
                    self.assertEqual(
                        entity["entity_id"],
                        f"{domain}.{expected['entity_prefix']}{index}",
                    )
                    self.assertEqual(entity["config_entry_domain"], integration)
                    self.assertEqual(entity["config_entry_id"], expected["config_entry_id"])
                    self.assertEqual(entity["config_entry_title"], expected["config_entry_title"])
                    self.assertEqual(
                        entity["attributes"].get("friendly_name"),
                        entity["friendly_name"],
                    )

    def test_diagnostics_keep_expected_shape(self) -> None:
        """Diagnostics must preserve integration data while reducing host details."""
        for integration, path in DIAGNOSTIC_FIXTURES.items():
            with self.subTest(integration=integration):
                data = load_json(path)

                self.assertEqual(data["integration_manifest"]["domain"], integration)
                self.assertEqual(
                    set(data["home_assistant"]),
                    {"version", "installation_type"},
                )
                self.assertIn("data", data)
                self.assertTrue(data["data"])

    def test_redaction_removes_obvious_sensitive_values(self) -> None:
        """Fixtures committed to the repository must not contain obvious secrets."""
        for path in [*DIAGNOSTIC_FIXTURES.values(), *(item["path"] for item in TEMPLATE_FIXTURES.values())]:
            data = load_json(path)
            with self.subTest(path=path.name):
                for json_path, value in iter_scalars(data):
                    string_value = str(value)
                    joined_path = ".".join(json_path)

                    if SENSITIVE_KEY.search(json_path[-1]):
                        self.assertIn(
                            "REDACTED",
                            string_value,
                            msg=f"{path}: sensitive path not redacted: {joined_path}",
                        )

                    self.assertIsNone(
                        SUSPICIOUS_VALUE.search(string_value),
                        msg=f"{path}: suspicious value at {joined_path}",
                    )


if __name__ == "__main__":
    unittest.main()

