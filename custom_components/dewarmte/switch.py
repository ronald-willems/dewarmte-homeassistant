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
    "boost_mode": DeWarmteSwitchEntityDescription(
        key="boost_mode",
        name="Boost Mode",
        icon="mdi:rocket-launch",
        translation_key="boost_mode"
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create boost mode switch
    switches = [
        DeWarmteSwitch(
            coordinator=coordinator,
            setting_id="boost_mode",
            description=SWITCH_DESCRIPTIONS["boost_mode"]
        )
    ]
    
    async_add_entities(switches, True)

class DeWarmteSwitch(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SwitchEntity):
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
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success and
            self.coordinator.api.operation_settings is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.api.operation_settings:
            return None
            
        if self._setting_id == "boost_mode":
            return self.coordinator.api.operation_settings.advanced_boost_mode_control
            
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._setting_id == "boost_mode":
            try:
                # When turning on boost mode, we need to provide both boost mode and current thermostat delay
                current_settings = self.coordinator.api.operation_settings
                if current_settings:
                    await self.coordinator.api.async_update_operation_settings({
                        "advanced_boost_mode_control": True,
                        "advanced_thermostat_delay": current_settings.advanced_thermostat_delay
                    })
                    await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to turn on boost mode: %s", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._setting_id == "boost_mode":
            try:
                # When turning off boost mode, we need to provide both boost mode and current thermostat delay
                current_settings = self.coordinator.api.operation_settings
                if current_settings:
                    await self.coordinator.api.async_update_operation_settings({
                        "advanced_boost_mode_control": False,
                        "advanced_thermostat_delay": current_settings.advanced_thermostat_delay
                    })
                    await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to turn off boost mode: %s", err) 