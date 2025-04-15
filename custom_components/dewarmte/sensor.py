"""Support for DeWarmte sensors."""
from __future__ import annotations


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator

from .const import DOMAIN

from dataclasses import dataclass
from typing import Optional, Callable, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)
from .api.models.status_data import StatusData




async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte sensors."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create a sensor entity for each defined sensor
    entities = []
    for sensor_def in SENSOR_DEFINITIONS.values():
        if sensor_def.key in coordinator.data:
            entities.append(
                DeWarmteSensor(
                    coordinator=coordinator,
                    sensor_def=sensor_def,
                )
            )

    async_add_entities(entities)





@dataclass
class SensorDefinition:
    """Definition of a sensor's properties."""
    key: str                    # Internal key (e.g., "water_flow")
    name: str                   # Display name
    var_name: str              # Variable name in API response
    device_class: Optional[SensorDeviceClass]
    state_class: Optional[SensorStateClass]
    unit: Optional[str]
    convert_func: Callable     # Function to convert the value

SENSOR_DEFINITIONS: Dict[str, SensorDefinition] = {
    # Status sensors
    "water_flow": SensorDefinition(
        key="water_flow",
        name="Water Flow",
        var_name="water_flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        convert_func=float
    ),
    "supply_temperature": SensorDefinition(
        key="supply_temperature",
        name="Supply Temperature",
        var_name="supply_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "outdoor_temperature": SensorDefinition(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        var_name="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "heat_input": SensorDefinition(
        key="heat_input",
        name="Heat Input",
        var_name="heat_input",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "actual_temperature": SensorDefinition(
        key="actual_temperature",
        name="Actual Temperature",
        var_name="actual_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "electricity_consumption": SensorDefinition(
        key="electricity_consumption",
        name="Electricity Consumption",
        var_name="electricity_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "heat_output": SensorDefinition(
        key="heat_output",
        name="Heat Output",
        var_name="heat_output",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "gas_boiler": SensorDefinition(
        key="gas_boiler",
        name="Gas Boiler",
        var_name="gas_boiler",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=bool
    ),
    "thermostat": SensorDefinition(
        key="thermostat",
        name="Thermostat",
        var_name="thermostat",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=bool
    ),
    "target_temperature": SensorDefinition(
        key="target_temperature",
        name="Target Temperature",
        var_name="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "electric_backup_usage": SensorDefinition(
        key="electric_backup_usage",
        name="Electric Backup Usage",
        var_name="electric_backup_usage",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    # Operational status sensors
    "is_on": SensorDefinition(
        key="is_on",
        name="Is On",
        var_name="is_on",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=bool
    ),
    "fault_code": SensorDefinition(
        key="fault_code",
        name="Fault Code",
        var_name="fault_code",
        device_class=None,
        state_class=None,
        unit=None,
        convert_func=int
    ),
    "is_connected": SensorDefinition(
        key="is_connected",
        name="Is Connected",
        var_name="is_connected",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=bool
    ),
}     

class DeWarmteSensor(CoordinatorEntity, SensorEntity):
    """Representation of a DeWarmte sensor."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        sensor_def: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_def = sensor_def
        self._attr_unique_id = f"{coordinator.device.device_id}_{sensor_def.key}"
        self._attr_name = sensor_def.name
        self._attr_native_unit_of_measurement = sensor_def.unit
        self._attr_device_class = sensor_def.device_class
        self._attr_state_class = sensor_def.state_class
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return getattr(self.coordinator.data, self._sensor_def.key, None)
        return None 