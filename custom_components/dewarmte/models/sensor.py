"""Sensor models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional, Callable, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)

@dataclass
class DeviceSensor:
    """Device sensor model."""
    key: str
    name: str
    value: float | bool
    device_class: Optional[SensorDeviceClass]
    state_class: Optional[SensorStateClass]
    unit: Optional[str]

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
    "water_flow": SensorDefinition(
        key="water_flow",
        name="Water Flow",
        var_name="water_flow",
        device_class=SensorDeviceClass.WATER,
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
} 