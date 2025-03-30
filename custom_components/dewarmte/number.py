"""Number platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN

@dataclass
class DeWarmteNumberEntityDescription(NumberEntityDescription):
    """Class describing DeWarmte number entities."""
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0

TEMPERATURE_NUMBERS = {
    "heat_curve_s1_outside_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s1_outside_temp",
        name="Heat Curve S1 Outside Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=-20.0,
        max_value=40.0,
        step=0.5,
    ),
    "heat_curve_s1_target_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s1_target_temp",
        name="Heat Curve S1 Target Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=20.0,
        max_value=80.0,
        step=0.5,
    ),
    "heat_curve_s2_outside_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s2_outside_temp",
        name="Heat Curve S2 Outside Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=-20.0,
        max_value=40.0,
        step=0.5,
    ),
    "heat_curve_s2_target_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s2_target_temp",
        name="Heat Curve S2 Target Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=20.0,
        max_value=80.0,
        step=0.5,
    ),
    "heat_curve_fixed_temperature": DeWarmteNumberEntityDescription(
        key="heat_curve_fixed_temperature",
        name="Heat Curve Fixed Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=20.0,
        max_value=80.0,
        step=0.5,
    ),
    "heating_performance_backup_temperature": DeWarmteNumberEntityDescription(
        key="heating_performance_backup_temperature",
        name="Heating Performance Backup Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=-20.0,
        max_value=40.0,
        step=0.5,
    ),
    "cooling_temperature": DeWarmteNumberEntityDescription(
        key="cooling_temperature",
        name="Cooling Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
    ),
    "cooling_duration": DeWarmteNumberEntityDescription(
        key="cooling_duration",
        name="Cooling Duration",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="minutes",
        min_value=0.0,
        max_value=1440.0,  # 24 hours in minutes
        step=5.0,
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte number entities."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        DeWarmteNumberEntity(coordinator, description)
        for description in TEMPERATURE_NUMBERS.values()
    )

class DeWarmteNumberEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], NumberEntity):
    """Representation of a DeWarmte number entity."""

    entity_description: DeWarmteNumberEntityDescription

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.api.operation_settings:
            return None

        settings = self.coordinator.api.operation_settings
        key = self.entity_description.key

        if key.startswith("heat_curve_"):
            # Handle heat curve settings
            if key == "heat_curve_fixed_temperature":
                return settings.heat_curve.fixed_temperature
            elif key == "heat_curve_s1_outside_temp":
                return settings.heat_curve.s1_outside_temp
            elif key == "heat_curve_s1_target_temp":
                return settings.heat_curve.s1_target_temp
            elif key == "heat_curve_s2_outside_temp":
                return settings.heat_curve.s2_outside_temp
            elif key == "heat_curve_s2_target_temp":
                return settings.heat_curve.s2_target_temp
        elif key == "heating_performance_backup_temperature":
            return settings.heating_performance_backup_temperature
        elif key == "cooling_temperature":
            return settings.cooling_temperature
        elif key == "cooling_duration":
            return settings.cooling_duration

        return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        key = self.entity_description.key
        settings = {}

        if key.startswith("heat_curve_"):
            # Handle heat curve settings
            if key == "heat_curve_fixed_temperature":
                settings["heat_curve_fixed_temperature"] = value
            elif key == "heat_curve_s1_outside_temp":
                settings["heat_curve_s1_outside_temp"] = value
            elif key == "heat_curve_s1_target_temp":
                settings["heat_curve_s1_target_temp"] = value
            elif key == "heat_curve_s2_outside_temp":
                settings["heat_curve_s2_outside_temp"] = value
            elif key == "heat_curve_s2_target_temp":
                settings["heat_curve_s2_target_temp"] = value
        elif key == "heating_performance_backup_temperature":
            settings["heating_performance_backup_temperature"] = value
        elif key == "cooling_temperature":
            settings["cooling_temperature"] = value
        elif key == "cooling_duration":
            settings["cooling_duration"] = value

        if settings:
            try:
                await self.coordinator.api.async_update_operation_settings(settings)
                await self.coordinator.async_request_refresh()
            except ValueError as err:
                _LOGGER.error("Failed to update setting %s: %s", key, str(err))
                raise 