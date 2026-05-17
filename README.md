# Home Assistant MQTT Device Bridge

A Home Assistant custom integration that publishes selected Home Assistant devices to MQTT for consumption by FHEM `MQTT2_DEVICE`.

The initial target is a bridge from Home Assistant's Overkiz and Miele integrations to FHEM. Both integrations expose one physical device as many Home Assistant entities across several domains, so the bridge is device-centric: one Home Assistant device becomes one FHEM `MQTT2_DEVICE`.

## Features

- Publishes whitelisted Home Assistant devices and their entities to MQTT.
- Device-centric: one HA device → one FHEM `MQTT2_DEVICE`.
- Generates FHEM raw config snippets (readingList, setList, webCmd, setStateList) automatically.
- Subscribes to MQTT command topics and translates them to HA service calls.
- UI-based setup via config flow and options flow (no YAML required).
- All state/metadata topics are retained; only changed readings are re-published on state changes.
- Readings payload includes a `last_change` timestamp (ISO 8601) of the most recent entity state change.
- Reading names have the common device prefix stripped; the primary entity is published as `state`.
- `republish` service action for manual re-broadcast of all retained topics.
- Diagnostics support with sensitive value redaction.

## Installation

Install via [HACS](https://hacs.xyz) as a custom repository:

1. HACS → ⋮ → Custom repositories → `https://github.com/bstaeheli/ha-mqtt-device-bridge` → Integration
2. Download and restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **Home Assistant MQTT Device Bridge**

## Configuration

### Initial setup

| Field | Default | Description |
|---|---|---|
| Name | Home Assistant MQTT Device Bridge | Integration entry name |
| MQTT topic prefix | `ha2fhem` | Root prefix for all published topics |
| MQTT QoS | `0` | QoS level for all publishes |

### Options (after setup)

| Field | Default | Description |
|---|---|---|
| MQTT topic prefix | `ha2fhem` | Root prefix for all published topics |
| MQTT QoS | `0` | QoS level for all publishes |
| Allowed integration domains | `overkiz,miele` | Comma-separated HA integration domains to bridge |

All MQTT messages are published with `retain=True`.

## MQTT Topic Contract

```text
<prefix>/<device_slug>/availability     → "online" / "offline"
<prefix>/<device_slug>/readings         → JSON state snapshot with last_change
<prefix>/<device_slug>/meta             → JSON device + entity metadata
<prefix>/<device_slug>/fhem/raw         → generated FHEM raw config snippet
<prefix>/<device_slug>/cmd/<entity_slug>/<command>  ← HA subscribes here
```

See [docs/fhem-mqtt2-architecture.md](docs/fhem-mqtt2-architecture.md) for the full design.

## FHEM Setup

1. Ensure FHEM has a `MQTT2_CLIENT` connected to the same broker.
2. Copy `fhem/ha_mqtt_device_bridge.attrTemplate` to your FHEM config directory and import it:
   ```
   attrTemplate import /path/to/ha_mqtt_device_bridge.attrTemplate
   ```
3. For each bridged device, take the generated raw config from the `fhem/raw` topic and paste it into FHEM, then apply the template:
   ```
   attr <DeviceName> attrTemplate ha_mqtt_device_bridge
   ```

## Development

Python tooling is managed with `uv`.

```sh
uv run pytest
```

Integration tests use `pytest-homeassistant-custom-component` and run against a real HA core instance.

## Release safety

This repo includes a GitHub Actions guard for tag pushes (`v*`):

- It compares `custom_components/ha_mqtt_device_bridge/manifest.json` `version` with the pushed tag.
- If they do not match (for example tag `v0.1.4` but manifest `0.1.3`), the workflow fails.
