"""Switch platform for DeWarmte integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

@dataclass
class DeWarmteSwitchEntityDescription(SwitchEntityDescription):
    """Class describing DeWarmte switch entities."""
    icon: str = None
    translation_key: str = None

SWITCH_DESCRIPTIONS = {
    "advanced_boost_mode_control": DeWarmteSwitchEntityDescription(
        key="advanced_boost_mode_control",
        name="Boost Mode",
        icon="mdi:rocket-launch"
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte switch platform."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setting up DeWarmte switch platform")

    entities = []
    for setting_id, description in SWITCH_DESCRIPTIONS.items():
        if coordinator.api.operation_settings is not None:
            entities.append(DeWarmteSwitchEntity(coordinator, setting_id, description))

    async_add_entities(entities)

class DeWarmteSwitchEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SwitchEntity):
    """Representation of a DeWarmte switch."""

    entity_description: DeWarmteSwitchEntityDescription

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        setting_id: str,
        description: DeWarmteSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._setting_id = setting_id
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{setting_id}"
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.api.operation_settings:
            return None

        return getattr(self.coordinator.api.operation_settings, self._setting_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.api.async_update_operation_settings({self._setting_id: True})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.api.async_update_operation_settings({self._setting_id: False})
        await self.coordinator.async_request_refresh() 