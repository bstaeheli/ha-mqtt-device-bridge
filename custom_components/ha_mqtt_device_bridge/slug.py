"""Slug helpers for MQTT topics and FHEM device names."""

from __future__ import annotations

import hashlib
import re
import unicodedata


_SEPARATORS = re.compile(r"[^a-zA-Z0-9]+")
_MULTIPLE_UNDERSCORES = re.compile(r"_+")


def ascii_slug(value: str, *, fallback: str = "device") -> str:
    """Return a lowercase ASCII slug suitable for MQTT topic path segments."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SEPARATORS.sub("_", ascii_value).strip("_").lower()
    slug = _MULTIPLE_UNDERSCORES.sub("_", slug)
    return slug or fallback


def fhem_device_name(name: str, device_id: str, *, prefix: str = "HA") -> str:
    """Generate a deterministic FHEM-safe device name."""
    base = ascii_slug(name, fallback="device")
    title_base = "_".join(part.capitalize() for part in base.split("_"))
    suffix = hashlib.sha1(device_id.encode("utf-8"), usedforsecurity=False).hexdigest()[:6]
    return f"{prefix}_{title_base}_{suffix}"

