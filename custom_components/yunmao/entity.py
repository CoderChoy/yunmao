"""Shared entity helpers for Yun Mao."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, YunMaoCoverDescription, YunMaoLightDescription
from .coordinator import YunMaoCoordinator


class YunMaoEntity(
    CoordinatorEntity[YunMaoCoordinator],
):
    """Base entity for Yun Mao devices."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: YunMaoCoordinator,
        description: YunMaoLightDescription | YunMaoCoverDescription,
    ) -> None:
        super().__init__(coordinator)
        self.description = description
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, description.device_identifier)},
            manufacturer="lierda-new",
            model=description.model,
            name=description.name,
        )
