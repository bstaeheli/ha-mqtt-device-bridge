"""FHEM MQTT2_DEVICE output helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FhemSetCommand:
    """A generated FHEM setList command."""

    name: str
    topic: str
    payload: str
    widget: str | None = None

    def render(self) -> str:
        """Render the setList line fragment."""
        setter = self.name if self.widget is None else f"{self.name}:{self.widget}"
        return f"{setter} {self.topic} {self.payload}"


@dataclass(frozen=True, slots=True)
class FhemDeviceConfig:
    """Generated FHEM MQTT2_DEVICE config."""

    device_name: str
    cid: str
    base_topic: str
    availability_topic: str
    readings_topic: str
    meta_topic: str
    fhem_raw_topic: str
    set_commands: tuple[FhemSetCommand, ...]
    web_commands: tuple[str, ...]
    set_state_commands: tuple[str, ...]

    def render_raw(self) -> str:
        """Render a FHEM raw config snippet."""
        lines = [
            f"defmod {self.device_name} MQTT2_DEVICE {self.cid}",
            f"attr {self.device_name} devicetopic {self.base_topic}",
            (
                f"attr {self.device_name} readingList "
                f"$DEVICETOPIC/availability:.* LWT\\\n"
                f"  $DEVICETOPIC/readings:.* {{ json2nameValue($EVENT) }}"
            ),
        ]

        if self.set_commands:
            lines.append(
                f"attr {self.device_name} setList "
                + "\\\n  ".join(
                    cmd.render().replace(f"{self.base_topic}/", "$DEVICETOPIC/")
                    for cmd in self.set_commands
                )
            )

        if self.set_state_commands:
            lines.append(
                f"attr {self.device_name} setStateList "
                + " ".join(self.set_state_commands)
            )

        if self.web_commands:
            lines.append(f"attr {self.device_name} webCmd {':'.join(self.web_commands)}")

        return "\n".join(lines)


def render_fhem_raw_configs(configs: Iterable[FhemDeviceConfig]) -> str:
    """Render multiple FHEM raw configs separated by blank lines."""
    return "\n\n".join(config.render_raw() for config in configs)
