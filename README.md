# Home Assistant MQTT Device Bridge

Planning repository for a Home Assistant custom integration that publishes selected Home Assistant devices to MQTT for consumption by FHEM `MQTT2_DEVICE`.

The initial target is a bridge from Home Assistant's Overkiz and Miele integrations to FHEM. Both integrations expose one physical device as many Home Assistant entities across several domains, so the bridge is device-centric: one Home Assistant device becomes one FHEM `MQTT2_DEVICE`.

## Goals

- Publish whitelisted Home Assistant devices and their entities to MQTT.
- Make the MQTT contract easy to consume from FHEM `MQTT2_DEVICE`.
- Allow FHEM to execute supported Home Assistant actions through simple command topics.
- Use modern Home Assistant integration patterns: UI config flow, options flow, typed runtime data, clean unload, diagnostics, tests, and Home Assistant's built-in MQTT APIs.
- Avoid YAML-only configuration in Home Assistant.

## Non-Goals For The First Version

- Generic Home Assistant MQTT Discovery.
- Arbitrary MQTT payloads that can call any Home Assistant service.
- Automatic execution of FHEM configuration commands from MQTT.
- Support for every Home Assistant integration on day one.

## Initial Scope

- Home Assistant Core: current modern APIs, starting with the 2026.x generation.
- Broker topology: Home Assistant and FHEM use the same MQTT broker independently.
- Source integrations: `overkiz` and `miele`.
- FHEM integration:
  - Generated FHEM raw config snippets.
  - A planned FHEM `attrTemplate` for repeatable setup.
  - Deterministic automatic FHEM device names on first implementation.

## Architecture

See [docs/fhem-mqtt2-architecture.md](docs/fhem-mqtt2-architecture.md) for the detailed design, MQTT topic contract, FHEM mapping, MVP checklist, and references.

