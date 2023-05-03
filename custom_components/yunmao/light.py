import asyncio
import json
import socket
import time
from datetime import timedelta
from io import BytesIO
from typing import Any

from homeassistant import config_entries
from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import (
    DOMAIN,
    CONF_INPUT_IP,
    CONF_NAME,
    CONF_MAC,
    CONF_POS,
    CONF_MAC2,
    CONF_POS2
)
from ...helpers.entity import DeviceInfo

SCAN_INTERVAL = timedelta(seconds=10)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if config_entry.options:
        config.update(config_entry.options)
    lights = [YunMaoLight(config_entry)]
    async_add_entities(lights, update_before_add=True)


async def query_light_is_on(ip_addr: str):
    reader, writer = await asyncio.open_connection(host=ip_addr, port=8888)
    # remove comment to test slow client
    body = "{\"sourceId\":\"" + ip_addr + "\",\"serialNum\":\"" + ip_addr + "\"," \
           "\"requestType\":\"query\",\"id\":\"0000000000000000\"}"
    writer.write(body.encode("utf8"))  # prepare data
    await writer.drain()  # send data

    if writer.can_write_eof():
        writer.write_eof()  # tell server that we sent all data

    # better use BytesIO than += if you gonna concat many times
    data_from_server = BytesIO()  # now get server answer
    result_json = None
    try:
        while True:
            # read chunk up to 8k bytes
            data = await asyncio.wait_for(reader.read(8192), timeout=5.0)
            data_from_server.write(data)
            # if server told use that no more data
            if reader.at_eof():
                break

        result_json = json.loads(data_from_server.getvalue().decode('utf8'))
    finally:
        writer.close()
        return result_json


class YunMaoLight(LightEntity):
    lastUpdateTime = 0
    result_json_cache = {}

    def __init__(self, entry: config_entries.ConfigEntry):
        self._ip_addr = entry.data[CONF_INPUT_IP]
        self._name = entry.data[CONF_NAME]
        self._mac = entry.data[CONF_MAC]
        self._pos = entry.data[CONF_POS]
        self._mac2 = entry.data[CONF_MAC2]
        self._pos2 = entry.data[CONF_POS2]
        self._last_op_time = 0

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
            body = "{\"sourceId\":\"" + self._ip_addr + "\",\"serialNum\":\"210431\",\"requestType\":\"cmd\",\"id\":\"" + \
                    mac + "\",\"attributes\":{\"KY" + pos + "\":\"ON\"}}"
        else:
            body = "{\"sourceId\":\"" + self._ip_addr + "\",\"serialNum\":\"210431\",\"requestType\":\"cmd\",\"id\":\"" + \
                   mac + "\",\"attributes\":{\"KY" + pos + "\":\"OFF\"}}"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((self._ip_addr, 8888))
        s.sendall(body.encode())
        self._attr_is_on = is_on
        self._last_op_time = time.time()

    def _update_is_on(self, status_data):
        if status_data is None:
            return
        swi = status_data["attributes"][self._mac]['SWI']
        if swi is not None:
            bits = int(self._pos)
            status = int(swi, 0)
            while bits > 1:
                status >>= 1
                bits -= 1
            self._attr_is_on = (status & 1 == 1)

    async def async_update(self) -> None:
        if time.time() - self._last_op_time < 30:
            return

        # 5秒内使用缓存（若有）
        cache = YunMaoLight.result_json_cache.get(self._ip_addr)
        if time.time() - YunMaoLight.lastUpdateTime < 5 and cache is not None:
            self._update_is_on(cache)
            return
        YunMaoLight.lastUpdateTime = time.time()

        result_json = await query_light_is_on(self._ip_addr)
        YunMaoLight.result_json_cache[self._ip_addr] = result_json
        self._update_is_on(result_json)

