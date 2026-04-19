"""Config flow for Yun Mao."""

from __future__ import annotations

import ipaddress
from typing import Any

from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol

from .client import YunMaoClient, YunMaoClientError
from .const import CONFIG_ENTRY_UNIQUE_ID, CONF_INPUT_IP, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_INPUT_IP, default="192.168.88.118"): str}
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


async def _async_validate_gateway(host: str) -> None:
    """Validate that the gateway is reachable."""

    try:
        await YunMaoClient(host).async_fetch_state()
    except YunMaoClientError as err:
        raise CannotConnect from err


class YunMaoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Yun Mao."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_INPUT_IP].strip()

            try:
                ipaddress.ip_address(host)
            except ValueError:
                errors["base"] = "address_not_valid"
            else:
                try:
                    await _async_validate_gateway(host)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(CONFIG_ENTRY_UNIQUE_ID)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="Yun Mao", data={CONF_INPUT_IP: host})

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
