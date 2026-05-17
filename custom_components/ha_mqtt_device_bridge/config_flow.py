"""Config flow for Home Assistant MQTT Device Bridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_RETAIN,
    CONF_TOPIC_PREFIX,
    DEFAULT_ALLOWED_INTEGRATIONS,
    DEFAULT_NAME,
    DEFAULT_QOS,
    DEFAULT_RETAIN,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)


class HaMqttDeviceBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={},
                options={
                    CONF_TOPIC_PREFIX: user_input[CONF_TOPIC_PREFIX],
                    CONF_QOS: user_input[CONF_QOS],
                    CONF_RETAIN: user_input[CONF_RETAIN],
                    CONF_ALLOWED_INTEGRATIONS: list(DEFAULT_ALLOWED_INTEGRATIONS),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): str,
                    vol.Required(CONF_QOS, default=DEFAULT_QOS): vol.In([0, 1, 2]),
                    vol.Required(CONF_RETAIN, default=DEFAULT_RETAIN): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return HaMqttDeviceBridgeOptionsFlow(config_entry)


class HaMqttDeviceBridgeOptionsFlow(OptionsFlowWithReload):
    """Handle bridge options."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage bridge options."""
        options = self._config_entry.options
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOPIC_PREFIX,
                        default=options.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX),
                    ): str,
                    vol.Required(
                        CONF_QOS,
                        default=options.get(CONF_QOS, DEFAULT_QOS),
                    ): vol.In([0, 1, 2]),
                    vol.Required(
                        CONF_RETAIN,
                        default=options.get(CONF_RETAIN, DEFAULT_RETAIN),
                    ): bool,
                    vol.Required(
                        CONF_ALLOWED_INTEGRATIONS,
                        default=",".join(
                            options.get(
                                CONF_ALLOWED_INTEGRATIONS,
                                DEFAULT_ALLOWED_INTEGRATIONS,
                            )
                        ),
                    ): str,
                }
            ),
        )

