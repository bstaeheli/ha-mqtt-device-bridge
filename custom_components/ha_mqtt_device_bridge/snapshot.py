"""Collect Home Assistant registry/state snapshots for bridge mapping."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def collect_device_template_exports(
    hass: HomeAssistant,
    *,
    allowed_integrations: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Collect template-export shaped snapshots for whitelisted HA devices."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    allowed = set(allowed_integrations)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    device_sources: dict[str, set[str]] = defaultdict(set)

    for registry_entry in entity_registry.entities.values():
        entity_id = registry_entry.entity_id
        integration_domain = getattr(registry_entry, "platform", None)
        device_id = getattr(registry_entry, "device_id", None)

        if not integration_domain or integration_domain not in allowed or not device_id:
            continue
        if getattr(registry_entry, "disabled_by", None) is not None:
            continue

        state = hass.states.get(entity_id)
        attributes = dict(state.attributes) if state is not None else {}
        friendly_name = attributes.get("friendly_name") or getattr(
            registry_entry, "name", None
        )
        config_entry_id = getattr(registry_entry, "config_entry_id", None)
        config_entry = (
            hass.config_entries.async_get_entry(config_entry_id)
            if config_entry_id
            else None
        )

        grouped[device_id].append(
            {
                "entity_id": entity_id,
                "domain": entity_id.split(".", 1)[0],
                "friendly_name": friendly_name,
                "state": state.state if state is not None else "unavailable",
                "attributes": attributes,
                "config_entry_id": config_entry_id,
                "config_entry_domain": integration_domain,
                "config_entry_title": config_entry.title if config_entry else None,
            }
        )
        device_sources[device_id].add(integration_domain)

    exports: list[dict[str, Any]] = []
    for device_id, entities in grouped.items():
        device = (
            device_registry.async_get(device_id)
            if hasattr(device_registry, "async_get")
            else device_registry.devices.get(device_id)
        )
        if device is None:
            continue

        device_name = (
            getattr(device, "name_by_user", None)
            or getattr(device, "name", None)
            or getattr(device, "model", None)
            or device_id
        )

        exports.append(
            {
                "export_version": 1,
                "root_entity": sorted(entity["entity_id"] for entity in entities)[0],
                "device_id": device_id,
                "device": {
                    "name": device_name,
                    "name_by_user": getattr(device, "name_by_user", None),
                    "manufacturer": getattr(device, "manufacturer", None),
                    "model": getattr(device, "model", None),
                    "model_id": getattr(device, "model_id", None),
                    "sw_version": getattr(device, "sw_version", None),
                    "hw_version": getattr(device, "hw_version", None),
                    "integration_domains": sorted(device_sources[device_id]),
                },
                "entities": sorted(entities, key=lambda entity: entity["entity_id"]),
            }
        )

    return sorted(exports, key=lambda export: export["device"]["name"])
