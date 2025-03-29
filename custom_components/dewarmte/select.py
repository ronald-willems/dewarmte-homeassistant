"""Select platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .models.settings import (
    HeatCurveMode,
    HeatingKind,
    HeatingPerformanceMode,
    SoundMode,
    PowerLevel,
)

@dataclass
class DeWarmteSelectEntityDescription(SelectEntityDescription):
    """Class describing DeWarmte select entities."""
    options_enum: type = None

MODE_SELECTS = {
    "heat_curve_mode": DeWarmteSelectEntityDescription(
        key="heat_curve_mode",
        name="Heat Curve Mode",
        options_enum=HeatCurveMode,
        options=[mode.value for mode in HeatCurveMode],
    ),
    "heating_kind": DeWarmteSelectEntityDescription(
        key="heating_kind",
        name="Heating Kind",
        options_enum=HeatingKind,
        options=[kind.value for kind in HeatingKind],
    ),
    "heating_performance_mode": DeWarmteSelectEntityDescription(
        key="heating_performance_mode",
        name="Heating Performance Mode",
        options_enum=HeatingPerformanceMode,
        options=[mode.value for mode in HeatingPerformanceMode],
    ),
    "sound_mode": DeWarmteSelectEntityDescription(
        key="sound_mode",
        name="Sound Mode",
        options_enum=SoundMode,
        options=[mode.value for mode in SoundMode],
    ),
    "sound_compressor_power": DeWarmteSelectEntityDescription(
        key="sound_compressor_power",
        name="Sound Compressor Power",
        options_enum=PowerLevel,
        options=[level.value for level in PowerLevel],
    ),
    "sound_fan_speed": DeWarmteSelectEntityDescription(
        key="sound_fan_speed",
        name="Sound Fan Speed",
        options_enum=PowerLevel,
        options=[level.value for level in PowerLevel],
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte select entities."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        DeWarmteSelectEntity(coordinator, description)
        for description in MODE_SELECTS.values()
    )

class DeWarmteSelectEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SelectEntity):
    """Representation of a DeWarmte select entity."""

    entity_description: DeWarmteSelectEntityDescription

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_options = description.options

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if not self.coordinator.api.operation_settings:
            return None

        settings = self.coordinator.api.operation_settings
        key = self.entity_description.key

        if key == "heat_curve_mode":
            return settings.heat_curve.mode.value
        elif key == "heating_kind":
            return settings.heat_curve.heating_kind.value
        elif key == "heating_performance_mode":
            return settings.heating_performance_mode.value
        elif key == "sound_mode":
            return settings.sound_mode.value
        elif key == "sound_compressor_power":
            return settings.sound_compressor_power.value
        elif key == "sound_fan_speed":
            return settings.sound_fan_speed.value

        return None

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        key = self.entity_description.key
        settings = {}

        if key == "heat_curve_mode":
            settings["heat_curve_mode"] = option
        elif key == "heating_kind":
            settings["heating_kind"] = option
        elif key == "heating_performance_mode":
            settings["heating_performance_mode"] = option
        elif key == "sound_mode":
            settings["sound_mode"] = option
        elif key == "sound_compressor_power":
            settings["sound_compressor_power"] = option
        elif key == "sound_fan_speed":
            settings["sound_fan_speed"] = option

        if settings:
            await self.coordinator.api.async_update_operation_settings(settings)
            await self.coordinator.async_request_refresh() 