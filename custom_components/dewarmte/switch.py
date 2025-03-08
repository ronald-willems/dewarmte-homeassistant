"""Switch platform for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCRIPTIONS = {
    "auto_heating": {
        "name": "Auto Heating",
        "icon": "mdi:radiator",
        "translation_key": "auto_heating"
    },
    "auto_cooling": {
        "name": "Auto Cooling",
        "icon": "mdi:snowflake",
        "translation_key": "auto_cooling"
    },
    "auto_tapwater": {
        "name": "Auto Tap Water",
        "icon": "mdi:water",
        "translation_key": "auto_tapwater"
    },
    "auto_legionella": {
        "name": "Auto Legionella Protection",
        "icon": "mdi:bacteria",
        "translation_key": "auto_legionella"
    },
    "auto_night": {
        "name": "Auto Night Mode",
        "icon": "mdi:weather-night",
        "translation_key": "auto_night"
    }
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Get current settings to create switches
    api = coordinator.api
    settings = await api.async_get_basic_settings()
    
    switches = []
    for setting_id, setting_data in settings.items():
        if setting_id in SWITCH_DESCRIPTIONS:
            switches.append(
                DeWarmteSwitch(
                    coordinator,
                    setting_id,
                    SWITCH_DESCRIPTIONS[setting_id]
                )
            )
    
    async_add_entities(switches, True)

class DeWarmteSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a DeWarmte switch."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        setting_id: str,
        description: dict[str, str],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._setting_id = setting_id
        self._attr_name = description["name"]
        self._attr_unique_id = f"{DOMAIN}_{setting_id}"
        self._attr_icon = description["icon"]
        self._attr_translation_key = description["translation_key"]
        self._attr_has_entity_name = True
        self._attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.data or self._setting_id not in self.coordinator.data:
            return None
        return self.coordinator.data[self._setting_id]["value"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self.coordinator.api.async_update_basic_setting(self._setting_id, True)
        if success:
            # Trigger an immediate data update
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self.coordinator.api.async_update_basic_setting(self._setting_id, False)
        if success:
            # Trigger an immediate data update
            await self.coordinator.async_request_refresh() 