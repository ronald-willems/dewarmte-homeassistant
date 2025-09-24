"""Constants for the DeWarmte integration."""
from typing import Final

from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)

# Integration domain
DOMAIN: Final = "dewarmte"

# Configuration constants
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 60  # 1 minute in seconds

# Sensor IDs
SENSOR_WATER_FLOW = "water_flow"
SENSOR_SUPPLY_TEMP = "supply_temperature"
SENSOR_OUTSIDE_TEMP = "outside_temperature"
SENSOR_HEAT_INPUT = "heat_input"
SENSOR_RETURN_TEMP = "return_temperature"
SENSOR_ELEC_CONSUMP = "electricity_consumption"
SENSOR_PUMP_AO_STATE = "pump_ao_state"
SENSOR_HEAT_OUTPUT = "heat_output"
SENSOR_BOILER_STATE = "boiler_state"
SENSOR_THERMOSTAT_STATE = "thermostat_state"
SENSOR_TOP_TEMP = "top_temperature"
SENSOR_BOTTOM_TEMP = "bottom_temperature"
SENSOR_HEAT_OUTPUT_PUMP_T = "heat_output_pump_t"
SENSOR_ELEC_CONSUMP_PUMP_T = "electricity_consumption_pump_t"
SENSOR_PUMP_T_STATE = "pump_t_state"
SENSOR_PUMP_T_HEATER_STATE = "pump_t_heater_state"
SENSOR_ROOM_TEMPERATURE = "room_temperature"
SENSOR_TARGET_TEMPERATURE = "target_temperature"
SENSOR_HEAT_DEMAND = "heat_demand"
SENSOR_VALVE_POSITION = "valve_position"
SENSOR_STATUS = "status"

# Switch IDs
SWITCH_DEFAULT_HEATING = "default_heating"
SWITCH_FORCE_BACKUP_ONLY = "force_backup_only"
SWITCH_FORCE_AO_ONLY = "force_ao_only"
SWITCH_BACKUP_ECO_MODE = "backup_eco_mode"
SWITCH_BACKUP_DEFAULT_MODE = "backup_default_mode"
SWITCH_BACKUP_COMFORT_MODE = "backup_comfort_mode"
SWITCH_SILENT_MODE = "silent_mode"

# Sensor groups by type
TEMPERATURE_SENSORS = [
    SENSOR_SUPPLY_TEMP,
    SENSOR_RETURN_TEMP,
    SENSOR_ROOM_TEMPERATURE,
    SENSOR_OUTSIDE_TEMP,
    SENSOR_TARGET_TEMPERATURE,
    SENSOR_TOP_TEMP,
    SENSOR_BOTTOM_TEMP,
]

PERCENTAGE_SENSORS = [
    SENSOR_HEAT_DEMAND,
    SENSOR_VALVE_POSITION,
]

ENERGY_SENSORS = [
    SENSOR_HEAT_INPUT,
    SENSOR_HEAT_OUTPUT,
    SENSOR_HEAT_OUTPUT_PUMP_T,
]

POWER_SENSORS = [
    SENSOR_ELEC_CONSUMP,
    SENSOR_ELEC_CONSUMP_PUMP_T,
]

FLOW_SENSORS = [
    SENSOR_WATER_FLOW,
]

STATE_SENSORS = [
    SENSOR_PUMP_AO_STATE,
    SENSOR_BOILER_STATE,
    SENSOR_THERMOSTAT_STATE,
    SENSOR_PUMP_T_STATE,
    SENSOR_PUMP_T_HEATER_STATE,
    SENSOR_STATUS,
]

# Unit mappings
SENSOR_UNITS = {
    **{sensor: UnitOfTemperature.CELSIUS for sensor in TEMPERATURE_SENSORS},
    **{sensor: PERCENTAGE for sensor in PERCENTAGE_SENSORS},
    **{sensor: UnitOfEnergy.KILO_WATT_HOUR for sensor in ENERGY_SENSORS},
    **{sensor: UnitOfPower.WATT for sensor in POWER_SENSORS},
    **{sensor: UnitOfVolumeFlowRate.LITERS_PER_MINUTE for sensor in FLOW_SENSORS},
}

# API endpoints
API_BASE_URL = "https://api.mydewarmte.com/v1"
API_LOGIN_ENDPOINT = "/auth/login"
API_DEVICE_ENDPOINT = "/devices"
API_SETTINGS_ENDPOINT = "/settings"

# Sensor attributes
ATTR_UNIT = "unit"
ATTR_VALUE = "value"

# Sensor display names
SENSOR_NAMES = {
    SENSOR_SUPPLY_TEMP: "Supply Temperature",
    SENSOR_RETURN_TEMP: "Return Temperature",
    SENSOR_ROOM_TEMPERATURE: "Room Temperature",
    SENSOR_OUTSIDE_TEMP: "Outside Temperature",
    SENSOR_TARGET_TEMPERATURE: "Target Temperature",
    SENSOR_HEAT_DEMAND: "Heat Demand",
    SENSOR_VALVE_POSITION: "Valve Position",
    SENSOR_STATUS: "Status"
} 