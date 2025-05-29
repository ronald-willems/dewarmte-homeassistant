"""Number platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from functools import cached_property

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.models.settings import SETTING_GROUPS

# Temperature constants
MIN_OUTSIDE_TEMP = -10.0
MAX_OUTSIDE_TEMP = 15.0
MIN_TARGET_TEMP = 0.0
MAX_TARGET_TEMP = 60.0
MIN_BACKUP_TEMP = -20.0
MAX_BACKUP_TEMP = 40.0
MIN_COOLING_TEMP = 10.0
MAX_COOLING_TEMP = 25.0

# Duration constants
MIN_COOLING_DURATION = 0
MAX_COOLING_DURATION = 259200  # 3 days in seconds

@dataclass(frozen=True)
class DeWarmteNumberEntityDescription(NumberEntityDescription):
    """Class describing DeWarmte number entities."""

TEMPERATURE_NUMBERS = {
    "heat_curve_s1_outside_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s1_outside_temp",
        name="Heat Curve S1 Outside Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_OUTSIDE_TEMP,
        native_max_value=MAX_OUTSIDE_TEMP,
        native_step=1.0,
    ),
    "heat_curve_s1_target_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s1_target_temp",
        name="Heat Curve S1 Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_TARGET_TEMP,
        native_max_value=MAX_TARGET_TEMP,
        native_step=1.0,
    ),
    "heat_curve_s2_outside_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s2_outside_temp",
        name="Heat Curve S2 Outside Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_OUTSIDE_TEMP,
        native_max_value=MAX_OUTSIDE_TEMP,
        native_step=1.0,
    ),
    "heat_curve_s2_target_temp": DeWarmteNumberEntityDescription(
        key="heat_curve_s2_target_temp",
        name="Heat Curve S2 Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_TARGET_TEMP,
        native_max_value=MAX_TARGET_TEMP,
        native_step=1.0,
    ),
    "heat_curve_fixed_temperature": DeWarmteNumberEntityDescription(
        key="heat_curve_fixed_temperature",
        name="Heat Curve Fixed Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_TARGET_TEMP,
        native_max_value=MAX_TARGET_TEMP,
        native_step=1.0,
    ),
    "heating_performance_backup_temperature": DeWarmteNumberEntityDescription(
        key="heating_performance_backup_temperature",
        name="Heating Performance Backup Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_BACKUP_TEMP,
        native_max_value=MAX_BACKUP_TEMP,
        native_step=1.0,
    ),
    "cooling_temperature": DeWarmteNumberEntityDescription(
        key="cooling_temperature",
        name="Cooling Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=MIN_COOLING_TEMP,
        native_max_value=MAX_COOLING_TEMP,
        native_step=1.0,
    ),
    "cooling_duration": DeWarmteNumberEntityDescription(
        key="cooling_duration",
        name="Cooling Duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=MIN_COOLING_DURATION,
        native_max_value=MAX_COOLING_DURATION,
        native_step=1.0,
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte number entities."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Filter out cooling entities if cooling is not supported
    entities = []
    for description in TEMPERATURE_NUMBERS.values():
        # Skip cooling entities if cooling is not supported
        if description.key in SETTING_GROUPS["cooling"].keys:
            assert coordinator.device is not None, "Coordinator device must not be None"
            if not coordinator.device.supports_cooling:
                continue
        entities.append(DeWarmteNumberEntity(coordinator, description))

    async_add_entities(entities)

class DeWarmteNumberEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], NumberEntity): # type: ignore[override]
    """Representation of a DeWarmte number entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteNumberEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteNumberEntityDescription, self.entity_description)

    @cached_property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.api.operation_settings:
            return None

        settings = self.coordinator.api.operation_settings
        key = self.dewarmte_description.key

        # Get the raw value and ensure it's a float
        value = getattr(settings, key, None)
        if value is None:
            return None
            
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.api.async_update_operation_settings(self.dewarmte_description.key, value)
        await self.coordinator.async_request_refresh() 