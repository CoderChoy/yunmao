"""Diagnostics support for Yun Mao."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_INPUT_IP, CONF_MAC, CONF_MAC2, CONF_NAME, DOMAIN
from .coordinator import YunMaoConfigEntry

TO_REDACT = {CONF_INPUT_IP, CONF_MAC, CONF_MAC2, CONF_NAME}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: YunMaoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    del hass

    return {
        "domain": DOMAIN,
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "runtime": entry.runtime_data.coordinator.diagnostics_data(),
    }
