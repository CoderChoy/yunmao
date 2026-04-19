"""Constants for the Yun Mao integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.const import Platform

DOMAIN = "yunmao"

CONF_PLATFORM = "platform"
CONF_INPUT_IP = "input_ip"
CONF_NAME = "name"
CONF_MAC = "mac"
CONF_POS = "pos"
CONF_MAC2 = "mac2"
CONF_POS2 = "pos2"

DEFAULT_POLL_INTERVAL = 30
GATEWAY_PORT = 8888
PUSH_PORT = 21688
CONFIG_ENTRY_UNIQUE_ID = DOMAIN


@dataclass(frozen=True, slots=True)
class YunMaoLightDescription:
    """Static description of a Yun Mao light entity."""

    name: str
    primary_mac: str
    primary_pos: int
    secondary_mac: str | None = None
    secondary_pos: int | None = None
    model: str = "switch-pln"

    @property
    def unique_id(self) -> str:
        """Return the entity unique id."""
        return self.name

    @property
    def device_identifier(self) -> str:
        """Return the device registry identifier."""
        return self.name


@dataclass(frozen=True, slots=True)
class YunMaoCoverDescription:
    """Static description of a Yun Mao cover entity."""

    name: str
    mac: str
    model: str = "covern"

    @property
    def unique_id(self) -> str:
        """Return the entity unique id."""
        return self.name

    @property
    def device_identifier(self) -> str:
        """Return the device registry identifier."""
        return self.name


LIGHT_DESCRIPTIONS: tuple[YunMaoLightDescription, ...] = (
    YunMaoLightDescription("灯带", "FFFF301B977B24F4", 1, "FFFF301B977B4D8E", 4),
    YunMaoLightDescription("客射灯", "FFFF301B977B24F4", 2, "FFFF301B977B4D8E", 5),
    YunMaoLightDescription("客主灯", "FFFF301B977B24F4", 3, "FFFF301B977B4D8E", 6),
    YunMaoLightDescription("玄关灯", "FFFF301B977B4D8E", 1, "FFFF301B977B24F4", 4),
    YunMaoLightDescription("鞋柜灯", "FFFF301B977B4D8E", 2, "FFFF301B977B24F4", 5),
    YunMaoLightDescription("餐主灯", "FFFF301B977B4D8E", 3, "FFFF301B977B24F4", 6),
    YunMaoLightDescription("厨房灯", "FFFF301B977B72F1", 2),
    YunMaoLightDescription("阳台灯", "FFFF301B977B16ED", 1),
    YunMaoLightDescription("客卫主灯", "FFFF301B977B549A", 1),
    YunMaoLightDescription("客卫镜灯", "FFFF301B977B549A", 2),
    YunMaoLightDescription("走廊灯", "FFFF301B977B549A", 3),
    YunMaoLightDescription("主卫镜灯", "FFFF301B977943F9", 1),
    YunMaoLightDescription("主卫主灯", "FFFF301B977943F9", 2),
)

COVER_DESCRIPTIONS: tuple[YunMaoCoverDescription, ...] = (
    YunMaoCoverDescription("窗帘", "00124B002471A560"),
    YunMaoCoverDescription("纱帘", "00124B0024D9D179"),
)

PLATFORMS: tuple[Platform, ...] = (Platform.LIGHT, Platform.COVER)


def is_legacy_entry_data(entry_data: Mapping[str, Any]) -> bool:
    """Return True if the config entry uses the legacy single-device shape."""

    return CONF_PLATFORM in entry_data and CONF_NAME in entry_data


def get_light_descriptions(entry_data: Mapping[str, Any]) -> tuple[YunMaoLightDescription, ...]:
    """Return all light descriptions for a config entry."""

    if not is_legacy_entry_data(entry_data):
        return LIGHT_DESCRIPTIONS

    if entry_data[CONF_PLATFORM] != Platform.LIGHT:
        return ()

    return (
        YunMaoLightDescription(
            name=entry_data[CONF_NAME],
            primary_mac=entry_data[CONF_MAC],
            primary_pos=int(entry_data[CONF_POS]),
            secondary_mac=entry_data.get(CONF_MAC2),
            secondary_pos=(
                int(entry_data[CONF_POS2]) if entry_data.get(CONF_POS2) is not None else None
            ),
        ),
    )


def get_cover_descriptions(entry_data: Mapping[str, Any]) -> tuple[YunMaoCoverDescription, ...]:
    """Return all cover descriptions for a config entry."""

    if not is_legacy_entry_data(entry_data):
        return COVER_DESCRIPTIONS

    if entry_data[CONF_PLATFORM] != Platform.COVER:
        return ()

    return (
        YunMaoCoverDescription(
            name=entry_data[CONF_NAME],
            mac=entry_data[CONF_MAC],
        ),
    )
