"""Configuration option helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_ALLOWED_INTEGRATIONS,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    DEFAULT_ALLOWED_INTEGRATIONS,
    DEFAULT_QOS,
    DEFAULT_TOPIC_PREFIX,
)


@dataclass(frozen=True, slots=True)
class BridgeOptions:
    """Normalized bridge options."""

    topic_prefix: str
    qos: int
    allowed_integrations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, options: Mapping[str, Any]) -> "BridgeOptions":
        """Build normalized options from a Home Assistant config entry mapping."""
        return cls(
            topic_prefix=str(options.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)).strip(
                "/ "
            )
            or DEFAULT_TOPIC_PREFIX,
            qos=int(options.get(CONF_QOS, DEFAULT_QOS)),
            allowed_integrations=parse_domain_csv(
                options.get(CONF_ALLOWED_INTEGRATIONS, DEFAULT_ALLOWED_INTEGRATIONS)
            ),
        )


def parse_domain_csv(value: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Parse a comma-separated domain list into normalized integration domains."""
    if isinstance(value, str):
        raw_domains = value.split(",")
    else:
        raw_domains = value

    domains = tuple(
        dict.fromkeys(
            domain.strip().lower()
            for domain in raw_domains
            if domain and domain.strip()
        )
    )
    return domains or DEFAULT_ALLOWED_INTEGRATIONS

