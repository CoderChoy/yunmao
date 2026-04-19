"""Cover platform for Yun Mao."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import YunMaoConfigEntry
from .entity import YunMaoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YunMaoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yun Mao cover entities."""

    del hass

    if not entry.runtime_data.coordinator.cover_descriptions:
        return

    async_add_entities(
        YunMaoCurtain(entry.runtime_data.coordinator, description)
        for description in entry.runtime_data.coordinator.cover_descriptions
    )


class YunMaoCurtain(YunMaoEntity, CoverEntity):
    """Representation of a Yun Mao curtain."""

    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    @property
    def is_opening(self) -> bool | None:
        """Return whether the cover is opening."""

        return self.coordinator.get_cover_state(self.description).is_opening

    @property
    def is_closing(self) -> bool | None:
        """Return whether the cover is closing."""

        return self.coordinator.get_cover_state(self.description).is_closing

    @property
    def is_closed(self) -> bool | None:
        """Return whether the cover is closed."""

        return self.coordinator.get_cover_state(self.description).is_closed

    @property
    def current_cover_position(self) -> int | None:
        """Return the current cover position."""

        return self.coordinator.get_cover_state(self.description).current_position

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""

        del kwargs
        await self.coordinator.async_open_cover(self.description)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""

        del kwargs
        await self.coordinator.async_close_cover(self.description)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""

        del kwargs
        await self.coordinator.async_stop_cover(self.description)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the target cover position."""

        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return

        await self.coordinator.async_set_cover_position(self.description, position)
