"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .entity import DeWarmteEntity

@dataclass
class DeWarmteSensorEntityDescription(SensorEntityDescription):
    """Class describing DeWarmte sensor entities."""
    var_name: str  # Variable name in API response
    convert_func: Callable  # Function to convert the value

SENSOR_DESCRIPTIONS: tuple[DeWarmteSensorEntityDescription, ...] = (
    # Status sensors
    DeWarmteSensorEntityDescription(
        key="water_flow",
        name="Water Flow",
        var_name="water_flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="supply_temperature",
        name="Supply Temperature",
        var_name="supply_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        var_name="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="heat_input",
        name="Heat Input",
        var_name="heat_input",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="actual_temperature",
        name="Actual Temperature",
        var_name="actual_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="electricity_consumption",
        name="Electricity Consumption",
        var_name="electricity_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="heat_output",
        name="Heat Output",
        var_name="heat_output",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="gas_boiler",
        name="Gas Boiler",
        var_name="gas_boiler",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
        convert_func=bool
    ),
    DeWarmteSensorEntityDescription(
        key="thermostat",
        name="Thermostat",
        var_name="thermostat",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
        convert_func=bool
    ),
    DeWarmteSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        var_name="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    DeWarmteSensorEntityDescription(
        key="electric_backup_usage",
        name="Electric Backup Usage",
        var_name="electric_backup_usage",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    # Operational status sensors
    DeWarmteSensorEntityDescription(
        key="is_on",
        name="Is On",
        var_name="is_on",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
        convert_func=bool
    ),
    DeWarmteSensorEntityDescription(
        key="fault_code",
        name="Fault Code",
        var_name="fault_code",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        convert_func=int
    ),
    DeWarmteSensorEntityDescription(
        key="is_connected",
        name="Is Connected",
        var_name="is_connected",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
        convert_func=bool
    ),
)

class DeWarmteSensor(DeWarmteEntity, SensorEntity):
    """Representation of a DeWarmte sensor."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        # The entity_description property automatically sets various attributes
        # including _attr_name from the description's name field
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return getattr(self.coordinator.data, self.entity_description.var_name, None)
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DeWarmte sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        DeWarmteSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ) 