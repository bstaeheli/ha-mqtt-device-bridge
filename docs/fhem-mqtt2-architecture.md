# FHEM MQTT2 Architecture Plan

## Context

This bridge is intended to connect Home Assistant devices to FHEM through a shared MQTT broker. FHEM and Home Assistant remain independent MQTT clients.

```text
Home Assistant Overkiz / Miele
        |
HA Custom Integration: ha_mqtt_device_bridge
        |
Shared MQTT broker
        |
FHEM MQTT2_CLIENT or MQTT2_SERVER
        |
FHEM MQTT2_DEVICE
```

The bridge should behave like a Home Assistant integration, not like a standalone daemon. It uses Home Assistant registries, state events, service calls, and the built-in MQTT integration.

## Current Decisions

- Target FHEM `MQTT2_DEVICE`, not generic Home Assistant MQTT Discovery.
- Use one FHEM `MQTT2_DEVICE` per Home Assistant device.
- Group all entities that belong to a Home Assistant device into that FHEM device.
- Use a whitelist with default-deny behavior.
- Allow filtering by Home Assistant integration domain, device, and entity.
- Initial whitelist focus: `overkiz` and `miele`.
- If a device is published, all supported actions for entities on that device are allowed.
- FHEM device names are generated automatically in the first implementation.
- Later versions may add a device-name mapping UI.
- Use generated FHEM raw config snippets and a FHEM `attrTemplate`.
- Do not let MQTT automatically execute FHEM `defmod` or `attr` commands in the default mode.

## Home Assistant Best Practices

The integration should follow current Home Assistant developer guidance:

- `manifest.json` declares `dependencies: ["mqtt"]`, `config_flow: true`, `integration_type: "hub"`, and an appropriate `iot_class`.
- `config_flow.py` creates the config entry through the UI.
- `options_flow.py` manages allowed integration domains, topic prefix, and QoS.
- Runtime objects are stored in `ConfigEntry.runtime_data`.
- `async_setup_entry` waits for MQTT availability before subscribing.
- All MQTT publishes use `retain=True` and an explicit `qos` value.
- State-change listeners publish only the `readings` topic for the affected device; `meta` and `fhem/raw` are only re-published on setup or explicit `republish` service call.
- Subscriptions and event listeners are removed in `async_unload_entry`.
- Integration service actions, for example `republish`, are registered in `async_setup`.
- Diagnostics redact sensitive values.
- Tests cover config flow, options flow, whitelist resolution, template mapping, MQTT command parsing, and unload cleanup.

## Broker And Topic Contract

Default topic prefix:

```text
ha2fhem
```

Per-device topics:

```text
ha2fhem/<device_slug>/availability
ha2fhem/<device_slug>/readings
ha2fhem/<device_slug>/meta
ha2fhem/<device_slug>/fhem/raw
ha2fhem/<device_slug>/cmd/<entity_slug>/<command>
```

Recommended behavior:

- `availability`: always retained, payload `online` or `offline`.
- `readings`: always retained JSON object for FHEM `json2nameValue($EVENT)`; includes `_ts` (ISO 8601 timestamp of the most recently changed entity). Re-published on every state change of a bridged entity.
- `meta`: always retained JSON object describing HA device, entities, available commands, and template decisions. Re-published only on setup or explicit `republish` service call.
- `fhem/raw`: always retained text containing generated FHEM raw config for manual import. Re-published only on setup or explicit `republish` service call.
- `cmd/...`: non-retained command topics subscribed by Home Assistant.

Example readings payload:

```json
{
  "state": "on",
  "fernsteuerung": "on",
  "programm": "cottons",
  "restzeit": 42,
  "tuer": "closed",
  "last_change": "2026-05-17T19:43:00+02:00"
}
```

Reading names are derived from entity object IDs with the common device prefix stripped.
The entity whose object ID matches the common prefix is published as ``state``.
The ``last_change`` field contains the ISO 8601 timestamp of the most recently changed entity.

Example command topics:

```text
ha2fhem/miele_washer/cmd/switch_power/set
ha2fhem/miele_washer/cmd/button_start/press
ha2fhem/miele_washer/cmd/select_mode/select
ha2fhem/living_room_cover/cmd/cover_living_room/open
ha2fhem/living_room_cover/cmd/cover_living_room/position
```

Command payloads are simple FHEM-friendly scalar values, not generic service-call JSON.

## FHEM Mapping

FHEM `MQTT2_DEVICE` works best when incoming data is handled through `readingList` and outgoing commands through `setList`. The bridge therefore publishes compact state JSON and exposes simple command topics.

Example generated raw config:

```text
defmod HA_Miele_Washer MQTT2_DEVICE ha2fhem_miele_washer
attr HA_Miele_Washer devicetopic ha2fhem/miele_washer
attr HA_Miele_Washer readingList $DEVICETOPIC/availability:.* LWT\
  $DEVICETOPIC/readings:.* { json2nameValue($EVENT) }
attr HA_Miele_Washer setList power:on,off $DEVICETOPIC/cmd/switch_power/set $EVTPART1\
  start:noArg $DEVICETOPIC/cmd/button_start/press 1\
  stop:noArg $DEVICETOPIC/cmd/button_stop/press 1
attr HA_Miele_Washer setStateList power:on,off
attr HA_Miele_Washer webCmd power:start:stop
```

Automatic FHEM creation strategy:

- FHEM can use `autocreate` and `bridgeRegexp` to create `MQTT2_DEVICE` instances from MQTT traffic.
- The bridge should still generate raw config because autocreate alone cannot reliably create the complete desired `setList`, `webCmd`, `devStateIcon`, and event tuning.
- A FHEM `attrTemplate` is planned so users can apply a consistent template to created devices.
- Full automatic execution of FHEM `defmod` or `attr` commands is intentionally out of the default scope because it would allow MQTT messages to change FHEM configuration.

## Device Name Strategy

Initial implementation:

- Generate FHEM device names deterministically from the Home Assistant device name.
- Prefix names with `HA_`.
- Normalize to FHEM-safe names: ASCII, spaces converted to `_`, unsupported characters removed, repeated separators collapsed.
- Resolve collisions by appending a short stable suffix derived from the Home Assistant device ID.

Example:

```text
Home Assistant device: "Miele Waschmaschine"
FHEM device name:      "HA_Miele_Waschmaschine"
MQTT device slug:      "miele_waschmaschine"
```

Future option:

- Add an options-flow mapping table for custom FHEM device names.

## Whitelist Model

Default behavior is deny-all.

Allow rules:

- Integration domains, for example `overkiz`, `miele`.
- Home Assistant device IDs.
- Home Assistant entity IDs.

Optional later exclude rules:

- Exclude specific devices from an allowed integration.
- Exclude specific entities from an allowed device.
- Exclude noisy attributes from a published entity.

Resolution order:

1. Load entity registry and device registry.
2. Select entities allowed by integration, device, or entity rule.
3. Group selected entities by Home Assistant device.
4. Drop groups with no supported readable or actionable entities.
5. Build templates and MQTT topics for each remaining device.

## Template Model

The bridge uses internal HA-to-FHEM templates. These are not Home Assistant YAML templates.

Each template decides:

- Reading names.
- Attribute filtering.
- Command names.
- FHEM widgets for `setList`.
- FHEM `webCmd`.
- FHEM `setStateList`.
- Whether an entity is read-only or actionable.

Initial domain templates:

| HA domain | Readings | Commands |
| --- | --- | --- |
| `sensor` | state, unit, selected attributes | none |
| `binary_sensor` | normalized on/off/open/closed state | none |
| `switch` | state | `set on/off`, `toggle` |
| `light` | state, brightness, color mode | `on`, `off`, `toggle`, `brightness`; RGB later |
| `button` | last state | `press` |
| `select` | current option | `select <option>` |
| `number` | numeric state | `set <number>` |
| `cover` | state, position, tilt if available | `open`, `close`, `stop`, `position`, `tilt` |
| `climate` | hvac mode, target/current temperature | `temperature`, `hvac_mode`, preset later |
| `fan` | state, percentage, preset if available | `on`, `off`, `percentage`, preset later |
| `vacuum` | state, fan speed | `start`, `pause`, `stop`, `return_to_base`, `fan_speed` |
| `water_heater` | operation mode, target/current temperature | `temperature`, `operation_mode` |
| `lock` | state | `lock`, `unlock` |
| `siren` | state | `turn_on`, `turn_off` |
| `scene` | exposed as available scene | `turn_on` |

Unsupported entities are listed in `meta` and diagnostics but are not exposed as commands.

## Overkiz Notes

Overkiz maps many physical devices to Home Assistant platforms such as alarm, binary sensor, button, climate, cover, light, lock, number, scene, select, sensor, siren, switch, and water heater.

Important limitations to preserve in docs and diagnostics:

- Some Overkiz devices do not broadcast state changes reliably.
- Stateless RTS covers may not report position or state.
- The Overkiz API can reject commands when the execution queue is full or the server is busy.
- Local API support differs from cloud API support.

The bridge should not invent missing state. It should publish what Home Assistant currently knows and expose availability/unavailable states clearly.

## Miele Notes

Miele appliances can expose binary sensors, buttons, climate entities, fan entities, lights, selects, sensors, switches, and vacuum entities.

Important limitations to preserve in docs and diagnostics:

- Entity availability depends on appliance type and generation.
- Some appliances do not report data while turned off.
- Several actions require MobileStart or remote-control mode to be active on the appliance.
- Program start actions may need Miele-specific service calls such as `miele.set_program` rather than a generic entity-domain service.

For the MVP, generic entity commands should be implemented first. Miele-specific program selection can be added after the base device bridge is stable.

## Implementation Checklist

1. Scaffold `custom_components/ha_mqtt_device_bridge`.
2. Add manifest, translations, config flow, options flow, diagnostics, and tests.
3. Implement typed config entry and runtime data.
4. Implement whitelist parsing and registry grouping.
5. Implement device-name and topic-slug generation.
6. Implement template engine for the initial HA domains.
7. Publish retained `availability`, `readings`, `meta`, and `fhem/raw`.
8. Subscribe to command topics and map them to Home Assistant service calls.
9. Register a `republish` service action in `async_setup`.
10. Add FHEM `attrTemplate` under a repo-level `fhem/` directory.
11. Add examples for Overkiz covers and Miele appliances.
12. Add tests for mappings, MQTT behavior, and unload cleanup.

## Open Questions For Implementation

- Exact minimum Home Assistant Core version once implementation starts.
- Whether to include a bootstrap FHEM notify for advanced users who accept MQTT-driven config changes.
- How broad the first Miele-specific action support should be beyond generic entity actions.
- Whether FHEM raw config should be exposed only via MQTT or also through a Home Assistant service response.

## References

- Home Assistant Developer Docs:
  - [Config flow](https://developers.home-assistant.io/docs/core/integration/config_flow)
  - [Options flow](https://developers.home-assistant.io/docs/core/integration/options_flow/)
  - [Integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
  - [Integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
  - [ConfigEntry runtime data](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/)
  - [Diagnostics](https://developers.home-assistant.io/docs/core/integration_diagnostics)
  - [MQTT publish API changes](https://developers.home-assistant.io/blog/2026/05/11/mqtt-publish-api-changes/)
- Home Assistant integration docs:
  - [Overkiz](https://www.home-assistant.io/integrations/overkiz/)
  - [Miele](https://www.home-assistant.io/integrations/miele/)
- FHEM documentation:
  - [MQTT2_DEVICE](https://wiki.fhem.de/wiki/MQTT2_DEVICE)
  - [MQTT2_DEVICE - Schritt fuer Schritt](https://wiki.fhem.de/wiki/MQTT2_DEVICE_-_Schritt_f%C3%BCr_Schritt)
  - [MQTT2_CLIENT](https://wiki.fhem.de/wiki/MQTT2_CLIENT)
  - [setList](https://fhemwiki.de/wiki/SetList)
