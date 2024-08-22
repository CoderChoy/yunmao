import logging
import socket
from typing import Any

from homeassistant import config_entries
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_INPUT_IP,
    CONF_MAC,
    CONF_MAC2,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_POS,
    CONF_POS2,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    if config_entry.data[CONF_PLATFORM] != Platform.LIGHT:
        _LOGGER.warning(
            "config_entry.data[CONF_PLATFORM] != Platform.LIGHT %s", config_entry.data
        )
        return
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if config_entry.options:
        config.update(config_entry.options)
    lights = [YunMaoLight(config_entry)]
    async_add_entities(lights, update_before_add=True)


class YunMaoLight(LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = ColorMode.ONOFF

    def __init__(self, entry: config_entries.ConfigEntry):
        self._ip_addr = entry.data[CONF_INPUT_IP]
        self._name = entry.data[CONF_NAME]
        self._mac = entry.data[CONF_MAC]
        self._pos = entry.data[CONF_POS]
        self._mac2 = entry.data[CONF_MAC2]
        self._pos2 = entry.data[CONF_POS2]
        self.get_ym_singleton().add_light_entity(self)

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def unique_id(self) -> str | None:
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="lierda-new",
            model="switch-pln",
            name=self._name,
        )
        return device_info

    def turn_on(self, **kwargs: Any) -> None:
        self._set_light_is_on(self._mac, self._pos, True)
        if self._mac2 is not None:
            self._set_light_is_on(self._mac2, self._pos2, True)

    def turn_off(self, **kwargs: Any) -> None:
        self._set_light_is_on(self._mac, self._pos, False)
        if self._mac2 is not None:
            self._set_light_is_on(self._mac2, self._pos2, False)

    def _set_light_is_on(self, mac, pos, is_on):
        if is_on:
            body = (
                '{"sourceId":"'
                + self._ip_addr
                + '","serialNum":"210431","requestType":"cmd","id":"'
                + mac
                + '","attributes":{"KY'
                + pos
                + '":"ON"}}'
            )
        else:
            body = (
                '{"sourceId":"'
                + self._ip_addr
                + '","serialNum":"210431","requestType":"cmd","id":"'
                + mac
                + '","attributes":{"KY'
                + pos
                + '":"OFF"}}'
            )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((self._ip_addr, 8888))
        s.sendall(body.encode())
        self._attr_is_on = is_on

    def get_ym_singleton(self):
        from .yunmao_data import ym_singleton
        return ym_singleton