"""Config flow for Home Assistant MQTT Device Bridge."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

try:  # Home Assistant is not available in the local test environment.
    from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
    from homeassistant.const import CONF_NAME
    from homeassistant.core import callback
    from homeassistant.data_entry_flow import FlowResult
except ModuleNotFoundError:  # pragma: no cover - import fallback for local tests
    class _FlowBase:
        """Fallback base class so the module stays importable without HA."""

        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

    class ConfigFlow(_FlowBase):
        """Fallback config flow base."""

    class OptionsFlowWithReload(_FlowBase):
        """Fallback options flow base."""

    CONF_NAME = "name"

    def callback(func):
        return func

    FlowResult = dict[str, Any]

if TYPE_CHECKING:
    import voluptuous as vol

from .const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    DEFAULT_ALLOWED_INTEGRATIONS,
    DEFAULT_NAME,
    DEFAULT_QOS,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)
from .options import parse_domain_csv


def _vol():
    """Import voluptuous lazily so module import works without HA deps."""
    import voluptuous as vol

    return vol


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
                    CONF_ALLOWED_INTEGRATIONS: list(DEFAULT_ALLOWED_INTEGRATIONS),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_vol().Schema(
                {
                    _vol().Required(CONF_NAME, default=DEFAULT_NAME): str,
                    _vol().Required(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): str,
                    _vol().Required(CONF_QOS, default=DEFAULT_QOS): _vol().In([0, 1, 2]),
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
            user_input[CONF_ALLOWED_INTEGRATIONS] = list(
                parse_domain_csv(user_input[CONF_ALLOWED_INTEGRATIONS])
            )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_vol().Schema(
                {
                    _vol().Required(
                        CONF_TOPIC_PREFIX,
                        default=options.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX),
                    ): str,
                    _vol().Required(
                        CONF_QOS,
                        default=options.get(CONF_QOS, DEFAULT_QOS),
                    ): _vol().In([0, 1, 2]),
                    _vol().Required(
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
