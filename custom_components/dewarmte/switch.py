"""Switch platform for DeWarmte integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast, final
from functools import cached_property

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.models.settings import SETTING_GROUPS

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class DeWarmteSwitchEntityDescription(SwitchEntityDescription):
    """Class describing DeWarmte switch entities."""
    icon: str | None = None
    translation_key: str | None = None

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
            entities.append(DeWarmteSwitchEntity(coordinator, description))

    async_add_entities(entities)

@final
class DeWarmteSwitchEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SwitchEntity):  # type: ignore[override]
    """Representation of a DeWarmte switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteSwitchEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteSwitchEntityDescription, self.entity_description)

    @cached_property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.api.operation_settings:
            return None

        return getattr(self.coordinator.api.operation_settings, self.dewarmte_description.key)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()
        # Clear the cached property
        if hasattr(self, "is_on"):
            delattr(self, "is_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        await self.coordinator.api.async_update_operation_settings(self.dewarmte_description.key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        await self.coordinator.api.async_update_operation_settings(self.dewarmte_description.key, False)
        await self.coordinator.async_request_refresh() 