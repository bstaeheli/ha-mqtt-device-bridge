"""Command mapping from FHEM MQTT topics to Home Assistant service calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .const import DEFAULT_TOPIC_PREFIX
from .slug import ascii_slug


class CommandError(ValueError):
    """Raised when a MQTT command cannot be mapped safely."""


@dataclass(frozen=True, slots=True)
class ServiceCallSpec:
    """A Home Assistant service call derived from a MQTT command."""

    domain: str
    service: str
    entity_id: str
    data: Mapping[str, Any]

    @property
    def service_data(self) -> dict[str, Any]:
        """Return service data including the target entity ID."""
        return {"entity_id": self.entity_id, **self.data}


@dataclass(frozen=True, slots=True)
class CommandDefinition:
    """A command allowed for a published Home Assistant entity."""

    topic: str
    entity_id: str
    domain: str
    command: str

    def service_call_for_payload(self, payload: str) -> ServiceCallSpec:
        """Map a scalar MQTT payload to a Home Assistant service call."""
        return service_call_for_command(
            entity_id=self.entity_id,
            domain=self.domain,
            command=self.command,
            payload=payload,
        )


def build_command_definitions(
    template_export: Mapping[str, Any],
    *,
    topic_prefix: str = DEFAULT_TOPIC_PREFIX,
) -> dict[str, CommandDefinition]:
    """Build allowed command definitions for a device template export."""
    device_slug = ascii_slug(template_export["device"]["name"], fallback="device")
    base_topic = f"{topic_prefix}/{device_slug}"
    definitions: dict[str, CommandDefinition] = {}

    for entity in template_export["entities"]:
        entity_id = entity["entity_id"]
        domain = entity["domain"]
        slug = ascii_slug(entity_id.replace(".", "_"), fallback="entity")
        for command in _commands_for_domain(domain, entity):
            topic = f"{base_topic}/cmd/{slug}/{command}"
            definitions[topic] = CommandDefinition(
                topic=topic,
                entity_id=entity_id,
                domain=domain,
                command=command,
            )

    return definitions


def service_call_for_command(
    *,
    entity_id: str,
    domain: str,
    command: str,
    payload: str,
) -> ServiceCallSpec:
    """Return a Home Assistant service call for an allowed scalar command."""
    value = payload.strip()

    if domain == "button" and command == "press":
        return ServiceCallSpec("button", "press", entity_id, {})

    if domain == "switch" and command == "set":
        if value == "on":
            return ServiceCallSpec("switch", "turn_on", entity_id, {})
        if value == "off":
            return ServiceCallSpec("switch", "turn_off", entity_id, {})
        if value == "toggle":
            return ServiceCallSpec("switch", "toggle", entity_id, {})
        raise CommandError(f"Unsupported switch payload: {value!r}")

    if domain == "light" and command == "set":
        if value == "on":
            return ServiceCallSpec("light", "turn_on", entity_id, {})
        if value == "off":
            return ServiceCallSpec("light", "turn_off", entity_id, {})
        if value == "toggle":
            return ServiceCallSpec("light", "toggle", entity_id, {})
        raise CommandError(f"Unsupported light payload: {value!r}")

    if domain == "number" and command == "set":
        return ServiceCallSpec(
            "number",
            "set_value",
            entity_id,
            {"value": _parse_number(value, field="value")},
        )

    if domain == "lock" and command == "set":
        if value == "lock":
            return ServiceCallSpec("lock", "lock", entity_id, {})
        if value == "unlock":
            return ServiceCallSpec("lock", "unlock", entity_id, {})
        raise CommandError(f"Unsupported lock payload: {value!r}")

    if domain == "cover":
        if command == "open":
            return ServiceCallSpec("cover", "open_cover", entity_id, {})
        if command == "close":
            return ServiceCallSpec("cover", "close_cover", entity_id, {})
        if command == "stop":
            return ServiceCallSpec("cover", "stop_cover", entity_id, {})
        if command == "position":
            return ServiceCallSpec(
                "cover",
                "set_cover_position",
                entity_id,
                {"position": _parse_percentage(value)},
            )

    if domain == "scene" and command == "turn_on":
        return ServiceCallSpec("scene", "turn_on", entity_id, {})

    if domain == "siren" and command == "set":
        if value == "on":
            return ServiceCallSpec("siren", "turn_on", entity_id, {})
        if value == "off":
            return ServiceCallSpec("siren", "turn_off", entity_id, {})
        raise CommandError(f"Unsupported siren payload: {value!r}")

    if domain == "select" and command == "select":
        if not value:
            raise CommandError("Select command requires a non-empty option")
        return ServiceCallSpec(
            "select",
            "select_option",
            entity_id,
            {"option": value},
        )

    raise CommandError(f"Unsupported command {domain}/{command}")


def _commands_for_domain(
    domain: str, entity: Mapping[str, Any]
) -> tuple[str, ...]:
    """Return command names exposed for a Home Assistant entity."""
    if domain == "button":
        return ("press",)
    if domain in {"switch", "light", "lock", "siren"}:
        return ("set",)
    if domain == "scene":
        return ("turn_on",)
    if domain == "number":
        return ("set",)
    if domain == "cover":
        return ("open", "close", "stop", "position")
    if domain == "select" and entity.get("attributes", {}).get("options"):
        return ("select",)
    return ()


def _parse_number(value: str, *, field: str) -> int | float:
    """Parse a numeric command payload."""
    try:
        parsed = float(value)
    except ValueError as err:
        raise CommandError(f"{field} must be numeric") from err

    if parsed.is_integer():
        return int(parsed)
    return parsed


def _parse_percentage(value: str) -> int:
    """Parse and validate a 0-100 percentage command payload."""
    parsed = _parse_number(value, field="position")
    if not isinstance(parsed, int):
        raise CommandError("position must be an integer percentage")
    if not 0 <= parsed <= 100:
        raise CommandError("position must be between 0 and 100")
    return parsed
