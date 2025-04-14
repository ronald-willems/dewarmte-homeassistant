"""Select platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from enum import Enum

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

class HeatCurveMode(str, Enum):
    """Heat curve mode settings."""
    WEATHER = "weather"
    FIXED = "fixed"

class HeatingKind(str, Enum):
    """Heating kind settings."""
    CUSTOM = "custom"
    FLOOR = "floor"
    RADIATOR = "radiator"
    BOTH = "both"

class HeatingPerformanceMode(str, Enum):
    """Heating performance mode settings."""
    AUTO = "auto"
    POMP_AO_ONLY = "pomp_ao_only"
    POMP_AO_AND_BACKUP = "pomp_ao_and_backup"
    BACKUP_ONLY = "backup_only"

class SoundMode(str, Enum):
    """Sound mode settings."""
    NORMAL = "normal"
    SILENT = "silent"

class PowerLevel(str, Enum):
    """Power level settings."""
    MIN = "min"
    MED = "med"
    MAX = "max"

class ThermostatDelay(str, Enum):
    """Thermostat delay settings."""
    MIN = "min"
    MED = "med"
    MAX = "max"

class BackupHeatingMode(str, Enum):
    """Backup heating mode settings."""
    AUTO = "auto"
    ECO = "eco"
    COMFORT = "comfort"

class CoolingThermostatType(str, Enum):
    """Cooling thermostat type settings."""
    HEATING_ONLY = "heating_only"
    HEATING_AND_COOLING = "heating_and_cooling"

class CoolingControlMode(str, Enum):
    """Cooling control mode settings."""
    THERMOSTAT = "thermostat"
    MANUAL = "manual"

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
    "advanced_thermostat_delay": DeWarmteSelectEntityDescription(
        key="advanced_thermostat_delay",
        name="Advanced Thermostat Delay",
        options_enum=ThermostatDelay,
        options=[delay.value for delay in ThermostatDelay],
    ),
    "backup_heating_mode": DeWarmteSelectEntityDescription(
        key="backup_heating_mode",
        name="Backup Heating Mode",
        options_enum=BackupHeatingMode,
        options=[mode.value for mode in BackupHeatingMode],
    ),
    "cooling_thermostat_type": DeWarmteSelectEntityDescription(
        key="cooling_thermostat_type",
        name="Cooling Thermostat Type",
        options_enum=CoolingThermostatType,
        options=[type.value for type in CoolingThermostatType],
    ),
    "cooling_control_mode": DeWarmteSelectEntityDescription(
        key="cooling_control_mode",
        name="Cooling Control Mode",
        options_enum=CoolingControlMode,
        options=[mode.value for mode in CoolingControlMode],
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
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_options = description.options

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if not self.coordinator.api.operation_settings:
            return None

        settings = self.coordinator.api.operation_settings
        key = self.entity_description.key

        # For heat curve settings, we need to access the nested structure
        if key in ["heat_curve_mode", "heating_kind"]:
            return getattr(settings.heat_curve, key.replace("heat_curve_", ""), None)
        return getattr(settings, key, None)

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        key = self.entity_description.key
        settings = {key: option}

        await self.coordinator.api.async_update_operation_settings(settings)
        await self.coordinator.async_request_refresh() 