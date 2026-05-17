"""Home Assistant MQTT Device Bridge integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import DOMAIN, SERVICE_REPUBLISH

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

PLATFORMS = []

type HaMqttDeviceBridgeConfigEntry = ConfigEntry[BridgeRuntimeData]


@dataclass(slots=True)
class BridgeRuntimeData:
    """Runtime data for a loaded bridge config entry."""

    config_entry_id: str

    async def async_republish(self) -> None:
        """Republish bridge metadata and states."""
        # The MQTT manager will be wired in once the mapping layer is implemented.


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-level service actions."""
    import voluptuous as vol
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import config_validation as cv

    async def _handle_republish(call: ServiceCall) -> None:
        """Handle a manual republish request."""
        entry_id = call.data.get("config_entry_id")
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state == ConfigEntryState.LOADED
            and (entry_id is None or entry.entry_id == entry_id)
        ]

        if entry_id is not None and not entries:
            raise HomeAssistantError(f"Config entry {entry_id} is not loaded")

        for entry in entries:
            runtime_data = entry.runtime_data
            await runtime_data.async_republish()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REPUBLISH,
        _handle_republish,
        schema=vol.Schema({vol.Optional("config_entry_id"): cv.string}),
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: HaMqttDeviceBridgeConfigEntry
) -> bool:
    """Set up the bridge from a config entry."""
    from homeassistant.components import mqtt

    await mqtt.async_wait_for_mqtt_client(hass)
    entry.runtime_data = BridgeRuntimeData(config_entry_id=entry.entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HaMqttDeviceBridgeConfigEntry
) -> bool:
    """Unload a bridge config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
