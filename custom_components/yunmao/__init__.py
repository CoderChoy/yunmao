"""The Yun Mao integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .client import YunMaoClient
from .const import CONF_INPUT_IP, DOMAIN, PLATFORMS
from .coordinator import (
    YunMaoConfigEntry,
    YunMaoCoordinator,
    YunMaoRuntimeData,
    async_get_push_server,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Yun Mao integration."""

    del config
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: YunMaoConfigEntry) -> bool:
    """Set up Yun Mao from a config entry."""

    client = YunMaoClient(entry.data[CONF_INPUT_IP])
    coordinator = YunMaoCoordinator(hass, client, dict(entry.data))
    remove_push_listener = await async_get_push_server(hass).async_add_listener(
        coordinator.handle_push_payload
    )

    entry.async_on_unload(remove_push_listener)
    entry.runtime_data = YunMaoRuntimeData(client=client, coordinator=coordinator)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: YunMaoConfigEntry) -> bool:
    """Unload a Yun Mao config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
