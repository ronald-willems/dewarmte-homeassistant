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
    device_types: tuple[str, ...] = ("AO", "PT", "HC")  # Device types this switch applies to

SWITCH_DESCRIPTIONS = {
    "advanced_boost_mode_control": DeWarmteSwitchEntityDescription(
        key="advanced_boost_mode_control",
        name="Boost Mode",
        icon="mdi:rocket-launch",
        device_types=("AO",),  # AO-specific: boost mode for space heating
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte switch platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setting up DeWarmte switch platform")

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        # Filter switch descriptions by device type
        filtered_descriptions = [
            description for description in SWITCH_DESCRIPTIONS.values()
            if coordinator.device.device_type in description.device_types
        ]
        
        switches = [
            DeWarmteSwitchEntity(coordinator, description)
            for description in filtered_descriptions
            if hasattr(coordinator, '_cached_settings') and coordinator._cached_settings is not None
        ]
        
        _LOGGER.debug("Adding %d switches for device %s (type: %s)",
                     len(switches),
                     coordinator.device.device_id if coordinator.device else "unknown",
                     coordinator.device.device_type)
        
        if switches:
            async_add_entities(switches)

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
        # Settings are cached in coordinator, read from there
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return None

        settings = self.coordinator._cached_settings
        return getattr(settings, self.dewarmte_description.key) if settings else None

    # the switch is not updated when the coordinator is updated due to the cached property
    # this is a workaround to clear the cached property when the coordinator is updated
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()
        # Clear the cached property
        if hasattr(self, "is_on"):
            delattr(self, "is_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        await self.coordinator.api.async_update_operation_settings(self.coordinator.device, self.dewarmte_description.key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        await self.coordinator.api.async_update_operation_settings(self.coordinator.device, self.dewarmte_description.key, False)
        await self.coordinator.async_request_refresh() 