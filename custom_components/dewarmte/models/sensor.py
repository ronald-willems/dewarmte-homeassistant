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
class SensorDefinition:
    """Definition of a sensor's properties."""
    key: str                    # Internal key (e.g., "water_flow")
    name: str                   # Display name
    var_name: str              # Variable name in HTML (e.g., "WaterFlow")
    device_class: Optional[SensorDeviceClass]
    state_class: Optional[SensorStateClass]
    unit: Optional[str]
    convert_func: Callable     # Function to convert the value

SENSOR_DEFINITIONS: Dict[str, SensorDefinition] = {
    "water_flow": SensorDefinition(
        key="water_flow",
        name="Water Flow",
        var_name="WaterFlow",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        convert_func=float
    ),
    "supply_temp": SensorDefinition(
        key="supply_temp",
        name="Supply Temperature",
        var_name="SupplyTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "outside_temp": SensorDefinition(
        key="outside_temp",
        name="Outside Temperature",
        var_name="OutSideTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "heat_input": SensorDefinition(
        key="heat_input",
        name="Heat Input",
        var_name="HeatInput",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "return_temp": SensorDefinition(
        key="return_temp",
        name="Return Temperature",
        var_name="ReturnTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "elec_consump": SensorDefinition(
        key="elec_consump",
        name="Electricity Consumption",
        var_name="ElecConsump",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "pump_ao_state": SensorDefinition(
        key="pump_ao_state",
        name="Pump AO State",
        var_name="PompAoOnOff",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=int
    ),
    "heat_output": SensorDefinition(
        key="heat_output",
        name="Heat Output",
        var_name="HeatOutPut",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "boiler_state": SensorDefinition(
        key="boiler_state",
        name="Boiler State",
        var_name="BoilerOnOff",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=int
    ),
    "thermostat_state": SensorDefinition(
        key="thermostat_state",
        name="Thermostat State",
        var_name="ThermostatOnOff",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=int
    ),
    "top_temp": SensorDefinition(
        key="top_temp",
        name="Top Temperature",
        var_name="TopTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "bottom_temp": SensorDefinition(
        key="bottom_temp",
        name="Bottom Temperature",
        var_name="BottomTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        convert_func=float
    ),
    "heat_output_pump_t": SensorDefinition(
        key="heat_output_pump_t",
        name="Heat Output Pump T",
        var_name="HeatOutputPompT",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "elec_consump_pump_t": SensorDefinition(
        key="elec_consump_pump_t",
        name="Electricity Consumption Pump T",
        var_name="ElecConsumpPompT",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.KILO_WATT,
        convert_func=float
    ),
    "pump_t_state": SensorDefinition(
        key="pump_t_state",
        name="Pump T State",
        var_name="PompTOnOff",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=int
    ),
    "pump_t_heater_state": SensorDefinition(
        key="pump_t_heater_state",
        name="Pump T Heater State",
        var_name="PompTHeaterOnOff",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        unit=None,
        convert_func=int
    ),
} 