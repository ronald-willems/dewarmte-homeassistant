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
    "default_heating": {
        "name": "Default Heating",
        "icon": "mdi:radiator",
        "translation_key": "default_heating"
    },
    "force_backup_only": {
        "name": "Force Backup Only",
        "icon": "mdi:hvac",
        "translation_key": "force_backup_only"
    },
    "force_ao_only": {
        "name": "Force Heat Pump Only",
        "icon": "mdi:heat-pump",
        "translation_key": "force_ao_only"
    },
    "backup_eco_mode": {
        "name": "Backup Eco Mode",
        "icon": "mdi:leaf",
        "translation_key": "backup_eco_mode"
    },
    "backup_default_mode": {
        "name": "Backup Default Mode",
        "icon": "mdi:tune",
        "translation_key": "backup_default_mode"
    },
    "backup_comfort_mode": {
        "name": "Backup Comfort Mode",
        "icon": "mdi:sofa",
        "translation_key": "backup_comfort_mode"
    },
    "silent_mode": {
        "name": "Silent Mode",
        "icon": "mdi:volume-off",
        "translation_key": "silent_mode"
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
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{setting_id}"
        self._attr_icon = description["icon"]
        self._attr_translation_key = description["translation_key"]
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._setting_id in self.coordinator.data
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.data or self._setting_id not in self.coordinator.data:
            return None
        return self.coordinator.data[self._setting_id]["value"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            success = await self.coordinator.api.async_update_basic_setting(self._setting_id, True)
            if success:
                # Update coordinator data
                self.coordinator.data[self._setting_id] = {"value": True}
                self.async_write_ha_state()
                # Trigger an immediate data update
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn on %s", self._setting_id)
        except Exception as err:
            _LOGGER.error("Error turning on %s: %s", self._setting_id, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            success = await self.coordinator.api.async_update_basic_setting(self._setting_id, False)
            if success:
                # Update coordinator data
                self.coordinator.data[self._setting_id] = {"value": False}
                self.async_write_ha_state()
                # Trigger an immediate data update
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn off %s", self._setting_id)
        except Exception as err:
            _LOGGER.error("Error turning off %s: %s", self._setting_id, err) 