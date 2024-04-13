import logging
import socket
import time
from typing import Any

from homeassistant import config_entries
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INPUT_IP, CONF_MAC, CONF_NAME, CONF_PLATFORM, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    if config_entry.data[CONF_PLATFORM] != Platform.COVER:
        _LOGGER.warning(
            "config_entry.data[CONF_PLATFORM] != Platform.COVER %s", config_entry.data
        )
        return
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if config_entry.options:
        config.update(config_entry.options)
    curtains = [YunMaoCurtain(config_entry)]
    async_add_entities(curtains, update_before_add=True)


class YunMaoCurtain(CoverEntity):
    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_is_closed = False
    _attr_current_cover_position = 100

    def __init__(self, entry: config_entries.ConfigEntry):
        self._ip_addr = entry.data[CONF_INPUT_IP]
        self._name = entry.data[CONF_NAME]
        self._mac = entry.data[CONF_MAC]
        self._last_op_time = 0
        self._attr_is_closed = False
        self._attr_current_cover_position = 100

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
            model="covern",
            name=self._name,
        )
        return device_info

    @property
    def is_opening(self) -> bool | None:
        return time.time() - self._last_op_time <= 5

    @property
    def is_closing(self) -> bool | None:
        return time.time() - self._last_op_time <= 5

    def open_cover(self, **kwargs: Any) -> None:
        self._last_op_time = time.time()
        self._attr_is_closed = False
        self._attr_current_cover_position = 100
        self._set_cover_status("OPEN")

    def close_cover(self, **kwargs: Any) -> None:
        self._last_op_time = time.time()
        self._attr_is_closed = True
        self._attr_current_cover_position = 0
        self._set_cover_status("CLOSE")

    def stop_cover(self, **kwargs: Any) -> None:
        self._attr_is_closed = False
        self._attr_current_cover_position = 50
        self._set_cover_status("STOP")

    def _set_cover_status(self, status: str):
        body = (
            '{"sourceId":"'
            + self._ip_addr
            + '","serialNum":"210431","requestType":"cmd","id":"'
            + self._mac
            + '","attributes":{"WIN":"'
            + status
            + '"}}'
        )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._ip_addr, 8888))
        s.sendall(body.encode())

    def set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION)
        self._last_op_time = time.time()
        self._attr_is_closed = position == 0
        self._attr_current_cover_position = position
        body = (
            '{"sourceId":"'
            + self._ip_addr
            + '","serialNum":"210431","requestType":"cmd","id":"'
            + self._mac
            + '","attributes":{"LEV":"'
            + str(position)
            + '"}}'
        )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._ip_addr, 8888))
        s.sendall(body.encode())
