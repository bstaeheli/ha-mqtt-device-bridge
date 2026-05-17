"""Tests for diagnostics payload redaction markers."""

from __future__ import annotations

import unittest

from custom_components.ha_mqtt_device_bridge.diagnostics import TO_REDACT


class DiagnosticsTest(unittest.TestCase):
    """Validate diagnostics redaction coverage."""

    def test_sensitive_runtime_identifiers_are_redacted(self) -> None:
        """Diagnostics should redact identifiers that can reveal local setup details."""
        self.assertIn("config_entry_id", TO_REDACT)
        self.assertIn("device_id", TO_REDACT)
        self.assertIn("entity_id", TO_REDACT)


if __name__ == "__main__":
    unittest.main()

