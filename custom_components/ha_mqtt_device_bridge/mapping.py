"""Map Home Assistant device snapshots to FHEM MQTT2_DEVICE artifacts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from os.path import commonprefix
from typing import Any

from .command import build_command_definitions
from .const import DEFAULT_TOPIC_PREFIX
from .fhem import FhemDeviceConfig, FhemSetCommand
from .slug import ascii_slug, fhem_device_name


def entity_slug(entity_id: str) -> str:
    """Return the MQTT command slug for an entity ID."""
    return ascii_slug(entity_id.replace(".", "_"), fallback="entity")


def object_id(entity_id: str) -> str:
    """Return the object ID part of an entity ID."""
    return entity_id.split(".", 1)[1] if "." in entity_id else entity_id


def _entity_prefix(entities: list[Mapping[str, Any]]) -> str:
    """Return the common slug prefix shared by all entity object IDs in a device.

    Trailing underscores are stripped so the prefix is a clean word boundary.
    """
    slugs = [ascii_slug(object_id(e["entity_id"]), fallback="entity") for e in entities]
    if not slugs:
        return ""
    prefix = commonprefix(slugs).rstrip("_")
    return prefix


def _short_name(slug: str, prefix: str) -> str:
    """Strip a common device prefix from a reading or command name.

    If the slug exactly matches the prefix the entity is the primary entity
    and its reading is named ``state``.  If the slug starts with
    ``prefix_`` the prefix is stripped.  Otherwise the slug is returned as-is.
    """
    if not prefix:
        return slug
    if slug == prefix:
        return "state"
    if slug.startswith(prefix + "_"):
        return slug[len(prefix) + 1:]
    return slug


def build_readings_payload(template_export: Mapping[str, Any]) -> dict[str, Any]:
    """Build a compact FHEM readings payload from a template export."""
    entities = template_export["entities"]
    prefix = _entity_prefix(list(entities))
    payload: dict[str, Any] = {}
    timestamps: list[str] = []

    for entity in entities:
        raw_name = ascii_slug(object_id(entity["entity_id"]), fallback="entity")
        reading = _short_name(raw_name, prefix)
        payload[reading] = entity.get("state")

        if ts := entity.get("last_changed"):
            timestamps.append(ts)

        attributes = entity.get("attributes", {})
        if entity["domain"] == "cover":
            if "current_position" in attributes:
                payload[f"{reading}_position"] = attributes["current_position"]
            if "current_tilt_position" in attributes:
                payload[f"{reading}_tilt_position"] = attributes[
                    "current_tilt_position"
                ]

    if timestamps:
        payload["last_change"] = max(timestamps)

    return payload


def build_meta_payload(
    template_export: Mapping[str, Any],
    *,
    topic_prefix: str = DEFAULT_TOPIC_PREFIX,
) -> dict[str, Any]:
    """Build retained metadata for a published bridge device."""
    fhem_config = build_fhem_device_config(
        template_export,
        topic_prefix=topic_prefix,
    )
    commands = build_command_definitions(
        template_export,
        topic_prefix=topic_prefix,
    )

    return {
        "device": template_export["device"],
        "device_id": template_export["device_id"],
        "fhem_device_name": fhem_config.device_name,
        "mqtt": {
            "availability_topic": fhem_config.availability_topic,
            "readings_topic": fhem_config.readings_topic,
            "command_topics": sorted(commands),
        },
        "entities": [
            {
                "entity_id": entity["entity_id"],
                "domain": entity["domain"],
                "friendly_name": entity.get("friendly_name"),
            }
            for entity in template_export["entities"]
        ],
    }


def build_fhem_device_config(
    template_export: Mapping[str, Any],
    *,
    topic_prefix: str = DEFAULT_TOPIC_PREFIX,
) -> FhemDeviceConfig:
    """Build a FHEM MQTT2_DEVICE config from a Home Assistant template export."""
    device = template_export["device"]
    device_id = template_export["device_id"]
    device_name = fhem_device_name(device["name"], device_id)
    device_slug = ascii_slug(device["name"], fallback="device")
    base_topic = f"{topic_prefix}/{device_slug}"
    entities = template_export["entities"]
    prefix = _entity_prefix(list(entities))

    commands: list[FhemSetCommand] = []
    web_commands: list[str] = []
    set_state_commands: list[str] = []

    for entity in entities:
        commands.extend(_commands_for_entity(base_topic, entity, prefix))

    seen_commands: Counter[str] = Counter()
    unique_commands: list[FhemSetCommand] = []
    for command in commands:
        seen_commands[command.name] += 1
        if seen_commands[command.name] == 1:
            unique_commands.append(command)
        else:
            unique_commands.append(
                FhemSetCommand(
                    name=f"{command.name}_{seen_commands[command.name]}",
                    widget=command.widget,
                    topic=command.topic,
                    payload=command.payload,
                )
            )

    for command in unique_commands:
        web_commands.append(command.name)
        if command.widget and ("on,off" in command.widget or "slider" in command.widget):
            set_state_commands.append(f"{command.name}:{command.widget}")

    return FhemDeviceConfig(
        device_name=device_name,
        cid=f"{topic_prefix}_{device_slug}",
        base_topic=base_topic,
        availability_topic=f"{base_topic}/availability",
        readings_topic=f"{base_topic}/readings",
        meta_topic=f"{base_topic}/meta",
        fhem_raw_topic=f"{base_topic}/fhem/raw",
        set_commands=tuple(unique_commands),
        web_commands=tuple(web_commands),
        set_state_commands=tuple(set_state_commands),
    )


def _commands_for_entity(
    base_topic: str, entity: Mapping[str, Any], prefix: str = ""
) -> tuple[FhemSetCommand, ...]:
    """Build FHEM set commands for one entity snapshot."""
    entity_id = entity["entity_id"]
    domain = entity["domain"]
    raw_name = ascii_slug(object_id(entity_id), fallback=domain)
    name = _short_name(raw_name, prefix)
    slug = entity_slug(entity_id)
    command_topic = f"{base_topic}/cmd/{slug}"

    if domain == "button":
        return (
            FhemSetCommand(
                name=name,
                widget="noArg",
                topic=f"{command_topic}/press",
                payload="1",
            ),
        )

    if domain == "switch":
        return (
            FhemSetCommand(
                name=name,
                widget="on,off,toggle",
                topic=f"{command_topic}/set",
                payload="$EVTPART1",
            ),
        )

    if domain == "light":
        return (
            FhemSetCommand(
                name=name,
                widget="on,off,toggle",
                topic=f"{command_topic}/set",
                payload="$EVTPART1",
            ),
        )

    if domain == "number":
        attributes = entity.get("attributes", {})
        minimum = attributes.get("min", 0)
        maximum = attributes.get("max", 100)
        step = attributes.get("step", 1)
        return (
            FhemSetCommand(
                name=name,
                widget=(
                    f"slider,{_format_widget_number(minimum)},"
                    f"{_format_widget_number(step)},"
                    f"{_format_widget_number(maximum)}"
                ),
                topic=f"{command_topic}/set",
                payload="$EVTPART1",
            ),
        )

    if domain == "lock":
        return (
            FhemSetCommand(
                name=name,
                widget="lock,unlock",
                topic=f"{command_topic}/set",
                payload="$EVTPART1",
            ),
        )

    if domain == "siren":
        return (
            FhemSetCommand(
                name=name,
                widget="on,off",
                topic=f"{command_topic}/set",
                payload="$EVTPART1",
            ),
        )

    if domain == "scene":
        return (
            FhemSetCommand(
                name=name,
                widget="noArg",
                topic=f"{command_topic}/turn_on",
                payload="1",
            ),
        )

    if domain == "cover":
        return (
            FhemSetCommand(
                name=f"{name}_open",
                widget="noArg",
                topic=f"{command_topic}/open",
                payload="1",
            ),
            FhemSetCommand(
                name=f"{name}_close",
                widget="noArg",
                topic=f"{command_topic}/close",
                payload="1",
            ),
            FhemSetCommand(
                name=f"{name}_stop",
                widget="noArg",
                topic=f"{command_topic}/stop",
                payload="1",
            ),
            FhemSetCommand(
                name=f"{name}_position",
                widget="slider,0,1,100",
                topic=f"{command_topic}/position",
                payload="$EVTPART1",
            ),
        )

    if domain == "select":
        options = entity.get("attributes", {}).get("options", [])
        if not options:
            return ()
        widget = ",".join(str(option) for option in options)
        return (
            FhemSetCommand(
                name=name,
                widget=widget,
                topic=f"{command_topic}/select",
                payload="$EVTPART1",
            ),
        )

    return ()


def _format_widget_number(value: Any) -> str:
    """Render a FHEM widget number without unnecessary decimal places."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
