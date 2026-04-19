"""Light platform for Yun Mao."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import YunMaoConfigEntry
from .entity import YunMaoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YunMaoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yun Mao light entities."""

    del hass

    if not entry.runtime_data.coordinator.light_descriptions:
        return

    async_add_entities(
        YunMaoLight(entry.runtime_data.coordinator, description)
        for description in entry.runtime_data.coordinator.light_descriptions
    )


class YunMaoLight(YunMaoEntity, LightEntity):
    """Representation of a Yun Mao light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool | None:
        """Return whether the light is on."""

        return self.coordinator.is_light_on(self.description)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""

        del kwargs
        await self.coordinator.async_set_light_state(self.description, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""

        del kwargs
        await self.coordinator.async_set_light_state(self.description, False)
