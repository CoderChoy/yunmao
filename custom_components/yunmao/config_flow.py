import logging
import socket
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import Platform
from .const import (
    DOMAIN,
    CONF_PLATFORM,
    CONF_INPUT_IP,
    CONF_NAME,
    CONF_MAC,
    CONF_POS,
    CONF_MAC2,
    CONF_POS2)

_LOGGER = logging.getLogger(__name__)

IP_SCHEMA = vol.Schema(
    {vol.Optional(CONF_INPUT_IP, default='192.168.88.118'): str}
)
LIGHT_DEVICES = {"灯带": {CONF_MAC: "FFFF301B977B24F4", CONF_POS: "1", CONF_MAC2: "FFFF301B977B4D8E", CONF_POS2: "4"},
                 "客射灯": {CONF_MAC: "FFFF301B977B24F4", CONF_POS: "2", CONF_MAC2: "FFFF301B977B4D8E", CONF_POS2: "5"},
                 "客主灯": {CONF_MAC: "FFFF301B977B24F4", CONF_POS: "3", CONF_MAC2: "FFFF301B977B4D8E", CONF_POS2: "6"},
                 "玄关灯": {CONF_MAC: "FFFF301B977B4D8E", CONF_POS: "1", CONF_MAC2: "FFFF301B977B24F4", CONF_POS2: "4"},
                 "鞋柜灯": {CONF_MAC: "FFFF301B977B4D8E", CONF_POS: "2", CONF_MAC2: "FFFF301B977B24F4", CONF_POS2: "5"},
                 "餐主灯": {CONF_MAC: "FFFF301B977B4D8E", CONF_POS: "3", CONF_MAC2: "FFFF301B977B24F4", CONF_POS2: "6"},
                 "厨房灯": {CONF_MAC: "FFFF301B977B72F1", CONF_POS: "2", CONF_MAC2: None, CONF_POS2: None},
                 "阳台灯": {CONF_MAC: "FFFF301B977B16ED", CONF_POS: "1", CONF_MAC2: None, CONF_POS2: None},
                 "客卫主灯": {CONF_MAC: "FFFF301B977B549A", CONF_POS: "1", CONF_MAC2: None, CONF_POS2: None},
                 "客卫镜灯": {CONF_MAC: "FFFF301B977B549A", CONF_POS: "2", CONF_MAC2: None, CONF_POS2: None},
                 "走廊灯": {CONF_MAC: "FFFF301B977B549A", CONF_POS: "3", CONF_MAC2: None, CONF_POS2: None},
                 "主卫镜灯": {CONF_MAC: "FFFF301B977943F9", CONF_POS: "1", CONF_MAC2: None, CONF_POS2: None},
                 "主卫主灯": {CONF_MAC: "FFFF301B977943F9", CONF_POS: "2", CONF_MAC2: None, CONF_POS2: None}}

CURTAIN_DEVICES = {"窗帘": "00124B002471A560",
                   "纱帘": "00124B0024D9D179"}


class GithubCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Custom config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                self._validate_ip_address(user_input[CONF_INPUT_IP])
            except ValueError:
                errors["base"] = "address_not_valid"
            if not errors:
                # Input is valid, set data.
                self.data = None
                for name in LIGHT_DEVICES.keys():
                    if self._already_configured(name):
                        continue
                    value = LIGHT_DEVICES[name]
                    self.data = {
                        CONF_PLATFORM: Platform.LIGHT,
                        CONF_INPUT_IP: user_input[CONF_INPUT_IP],
                        CONF_NAME: name,
                        CONF_MAC: value[CONF_MAC],
                        CONF_POS: value[CONF_POS],
                        CONF_MAC2: value[CONF_MAC2],
                        CONF_POS2: value[CONF_POS2]}
                    break

                if self.data is None:
                    for name in CURTAIN_DEVICES.keys():
                        if self._already_configured(name):
                            continue
                        mac = CURTAIN_DEVICES[name]
                        self.data = {
                            CONF_PLATFORM: Platform.COVER,
                            CONF_INPUT_IP: user_input[CONF_INPUT_IP],
                            CONF_NAME: name,
                            CONF_MAC: mac}
                        break

                if self.data is not None:
                    # Return the form of the next step.
                    return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)
                else:
                    errors["base"] = ""

        return self.async_show_form(
            step_id="user", data_schema=IP_SCHEMA, errors=errors
        )

    def _already_configured(self, name):
        for entry in self._async_current_entries():
            if name == entry.data.get(CONF_NAME):
                return True
        return False

    def _validate_ip_address(self, ip_address):
        try:
            socket.inet_aton(ip_address)
        except socket.error:
            raise ValueError
