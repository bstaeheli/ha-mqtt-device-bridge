"""Runtime MQTT publisher/subscriber for the bridge."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .command import CommandDefinition, CommandError, build_command_definitions
from .mapping import (
    build_fhem_device_config,
    build_meta_payload,
    build_readings_payload,
)
from .options import BridgeOptions
from .snapshot import collect_device_template_exports

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)


class MqttBridgeRuntime:
    """Runtime for one bridge config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the bridge runtime."""
        self.hass = hass
        self.entry = entry
        self.options = BridgeOptions.from_mapping(entry.options)
        self._unsubscribers: list[Callable[[], None]] = []
        self._command_definitions: dict[str, CommandDefinition] = {}
        self._last_exports: list[dict[str, Any]] = []
        # Map entity_id → export for efficient state-change updates
        self._entity_to_export: dict[str, dict[str, Any]] = {}

    async def async_setup(self) -> None:
        """Start publishing and listening for MQTT commands."""
        from homeassistant.components import mqtt
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_state_change_event

        await self.async_republish()

        @callback
        def _message_received(msg) -> None:
            """Schedule MQTT command handling."""
            self.hass.async_create_task(
                self.async_handle_mqtt_message(msg.topic, msg.payload)
            )

        unsubscribe_mqtt = await mqtt.async_subscribe(
            self.hass,
            f"{self.options.topic_prefix}/+/cmd/#",
            _message_received,
            qos=self.options.qos,
        )
        self._unsubscribers.append(unsubscribe_mqtt)

        entity_ids = list(self._entity_to_export)
        if entity_ids:

            @callback
            def _state_changed(event: Event) -> None:
                """Publish only readings for the device whose entity changed."""
                entity_id = event.data.get("entity_id")
                self.hass.async_create_task(
                    self.async_publish_readings(entity_id)
                )

            self._unsubscribers.append(
                async_track_state_change_event(
                    self.hass,
                    entity_ids,
                    _state_changed,
                )
            )

    async def async_unload(self) -> None:
        """Stop MQTT subscriptions and mark exported devices offline."""
        while self._unsubscribers:
            self._unsubscribers.pop()()

        await self._publish_availability("offline")

    def diagnostics_data(self) -> dict[str, Any]:
        """Return runtime diagnostics."""
        return {
            "published_device_count": len(self._last_exports),
            "command_topic_count": len(self._command_definitions),
            "topic_prefix": self.options.topic_prefix,
            "qos": self.options.qos,
            "retain": True,
            "allowed_integrations": self.options.allowed_integrations,
            "devices": [
                {
                    "device_id": export["device_id"],
                    "name": export["device"]["name"],
                    "entity_count": len(export["entities"]),
                    "entities": [
                        {
                            "entity_id": entity["entity_id"],
                            "domain": entity["domain"],
                        }
                        for entity in export["entities"]
                    ],
                }
                for export in self._last_exports
            ],
        }

    async def async_republish(self) -> None:
        """Publish all bridge data (static + readings) for all allowed devices."""
        from homeassistant.components import mqtt

        exports = collect_device_template_exports(
            self.hass,
            allowed_integrations=self.options.allowed_integrations,
        )
        self._last_exports = exports
        self._command_definitions = {}
        self._entity_to_export = {
            entity["entity_id"]: export
            for export in exports
            for entity in export["entities"]
        }

        for export in exports:
            fhem_config = build_fhem_device_config(
                export,
                topic_prefix=self.options.topic_prefix,
            )
            readings_payload = build_readings_payload(export)
            meta_payload = build_meta_payload(
                export,
                topic_prefix=self.options.topic_prefix,
            )
            self._command_definitions.update(
                build_command_definitions(
                    export,
                    topic_prefix=self.options.topic_prefix,
                )
            )

            await mqtt.async_publish(
                self.hass,
                fhem_config.availability_topic,
                "online",
                self.options.qos,
                True,
            )
            await mqtt.async_publish(
                self.hass,
                fhem_config.readings_topic,
                json.dumps(readings_payload, sort_keys=True),
                self.options.qos,
                True,
            )
            await mqtt.async_publish(
                self.hass,
                fhem_config.meta_topic,
                json.dumps(meta_payload, sort_keys=True),
                self.options.qos,
                True,
            )
            await mqtt.async_publish(
                self.hass,
                fhem_config.fhem_raw_topic,
                fhem_config.render_raw(),
                self.options.qos,
                True,
            )

    async def async_publish_readings(self, entity_id: str | None) -> None:
        """Publish only the readings topic for the device owning entity_id."""
        if entity_id is None:
            return
        export = self._entity_to_export.get(entity_id)
        if export is None:
            return
        from homeassistant.components import mqtt

        # Re-fetch current state for this export's entities
        fresh_exports = collect_device_template_exports(
            self.hass,
            allowed_integrations=self.options.allowed_integrations,
        )
        device_id = export["device_id"]
        fresh = next((e for e in fresh_exports if e["device_id"] == device_id), None)
        if fresh is None:
            return

        fhem_config = build_fhem_device_config(
            fresh,
            topic_prefix=self.options.topic_prefix,
        )
        readings_payload = build_readings_payload(fresh)
        await mqtt.async_publish(
            self.hass,
            fhem_config.readings_topic,
            json.dumps(readings_payload, sort_keys=True),
            self.options.qos,
            True,
        )

    async def async_handle_mqtt_message(self, topic: str, payload: Any) -> None:
        """Handle one MQTT command message."""
        command = self._command_definitions.get(topic)
        if command is None:
            _LOGGER.warning("Ignoring MQTT command for unknown topic: %s", topic)
            return

        try:
            service_call = command.service_call_for_payload(_payload_to_text(payload))
        except CommandError as err:
            _LOGGER.warning("Ignoring invalid MQTT command on %s: %s", topic, err)
            return

        await self.hass.services.async_call(
            service_call.domain,
            service_call.service,
            service_call.service_data,
            blocking=False,
        )

    async def _publish_availability(self, payload: str) -> None:
        """Publish availability for all previously exported devices."""
        from homeassistant.components import mqtt
        from homeassistant.exceptions import HomeAssistantError

        for export in self._last_exports:
            fhem_config = build_fhem_device_config(
                export,
                topic_prefix=self.options.topic_prefix,
            )
            try:
                await mqtt.async_publish(
                    self.hass,
                    fhem_config.availability_topic,
                    payload,
                    self.options.qos,
                    True,
                )
            except HomeAssistantError:
                _LOGGER.debug(
                    "MQTT unavailable while publishing availability (%s), skipping",
                    fhem_config.availability_topic,
                )


def _payload_to_text(payload: Any) -> str:
    """Convert a HA MQTT payload to text."""
    if isinstance(payload, bytes):
        return payload.decode()
    return str(payload)
