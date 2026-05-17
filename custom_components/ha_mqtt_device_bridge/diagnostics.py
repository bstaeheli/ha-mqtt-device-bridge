"""Diagnostics support for Home Assistant MQTT Device Bridge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

TO_REDACT = {
    "config_entry_id",
    "device_id",
    "entity_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    from homeassistant.components.diagnostics import async_redact_data

    runtime_data = getattr(entry, "runtime_data", None)
    manager = getattr(runtime_data, "manager", None)

    data: dict[str, Any] = {
        "domain": DOMAIN,
        "entry": {
            "title": entry.title,
            "state": getattr(entry.state, "name", str(entry.state)),
            "options": dict(entry.options),
        },
        "runtime": manager.diagnostics_data() if manager is not None else None,
    }

    return async_redact_data(data, TO_REDACT)
