"""Select platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from enum import Enum

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.client import DeWarmteApiError
from .api.models.settings import SETTING_GROUPS

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
    """Cooling control mode values known to the API.

    `FORCED` is listed for completeness but cannot be written: the cooling
    settings endpoint answers HTTP 400 `"forced" is not a valid choice.` for it.
    See SELECTABLE_COOLING_CONTROL_MODES.
    """
    THERMOSTAT = "thermostat"
    COOLING_ONLY = "cooling_only"
    HEATING_ONLY = "heating_only"
    FORCED = "forced"
    SCHEDULED = "scheduled"

# The modes a user may actually select. Forced ("cool now") cooling is not one
# of them: it is started and stopped by the dewarmte.start_forced_cooling /
# dewarmte.stop_forced_cooling services and reported by the "Forced Cooling
# Active" binary sensor, independent of this setting.
SELECTABLE_COOLING_CONTROL_MODES = [
    mode.value for mode in CoolingControlMode if mode is not CoolingControlMode.FORCED
]

# Weekday options for the legionella protection run. The API wants the number:
# OPTIONS settings/legionella/ -> actions.POST.legionella_protection_day.choices
# is 1 = Monday ... 7 = Sunday.
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
LEGIONELLA_DAY_VALUES = {name: number for number, name in enumerate(WEEKDAYS, start=1)}

@dataclass(frozen=True)
class DeWarmteSelectEntityDescription(SelectEntityDescription):
    """Class describing DeWarmte select entities."""
    options_enum: type[Enum] | None = None
    # Device types this select applies to. Most settings belong to the space
    # heating pumps; Pomp T has only its warm water settings.
    device_types: tuple[str, ...] = ("AO", "MP")
    # option -> value the API expects, for settings whose API values are not
    # the option strings themselves. None means the options are written as-is.
    api_values: dict[str, Any] | None = None

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
        options=SELECTABLE_COOLING_CONTROL_MODES,
    ),
    "legionella_protection_day": DeWarmteSelectEntityDescription(
        key="legionella_protection_day",
        name="Legionella Protection Day",
        options=WEEKDAYS,
        api_values=LEGIONELLA_DAY_VALUES,
        device_types=("PT",),  # PT-specific: weekly disinfecting run of the hot water tank
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte select entities."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        entities = []
        for description in MODE_SELECTS.values():
            if coordinator.device.device_type not in description.device_types:
                continue
            # Skip cooling entities if cooling is not supported
            if description.key in SETTING_GROUPS["cooling"].keys:
                assert coordinator.device is not None, "Coordinator device must not be None"
                if not coordinator.device.supports_cooling:
                    continue
            entities.append(DeWarmteSelectEntity(coordinator, description))

        async_add_entities(entities)

class DeWarmteSelectEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SelectEntity): # type: ignore[override]
    """Representation of a DeWarmte select entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        assert description.options is not None, "Select entity must have options"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_options = description.options

    @property
    def dewarmte_description(self) -> DeWarmteSelectEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteSelectEntityDescription, self.entity_description)

    @property
    def current_option(self) -> str | None:  # type: ignore[override]
        """Return the current selected option."""
        # Settings are cached in coordinator, read from there
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return None

        settings = self.coordinator._cached_settings
        description = self.dewarmte_description

        # All settings are now at the root level
        value = getattr(settings, description.key, None)
        if description.api_values is None or value is None:
            return value
        return next((option for option, api_value in description.api_values.items() if api_value == value), None)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        description = self.dewarmte_description
        value = option if description.api_values is None else description.api_values[option]
        try:
            await self.coordinator.async_write_setting(description.key, value)
        except DeWarmteApiError as err:
            # Surface the API's reason (e.g. a rejected value) instead of an
            # "Unexpected error" toast with no explanation.
            raise HomeAssistantError(str(err)) from err
