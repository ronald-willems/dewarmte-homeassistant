"""Constants for the DeWarmte integration."""
from typing import Final

DOMAIN: Final = "dewarmte"

# Configuration
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Sensors
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

# Sensor attributes
ATTR_UNIT = "unit"
ATTR_VALUE = "value"

# Update interval (in seconds)
UPDATE_INTERVAL = 60

# Configuration
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes

# Sensor types
SENSOR_ROOM_TEMPERATURE = "room_temperature"      # Kamer temperatuur
SENSOR_TARGET_TEMPERATURE = "target_temperature"  # Gewenste temperatuur
SENSOR_HEAT_DEMAND = "heat_demand"               # Warmtevraag (%)
SENSOR_VALVE_POSITION = "valve_position"         # Klepstand (%)
SENSOR_STATUS = "status"                         # System status

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

# Sensor classes
PERCENTAGE_SENSORS = [SENSOR_HEAT_DEMAND, SENSOR_VALVE_POSITION]
TEMPERATURE_SENSORS = [
    SENSOR_SUPPLY_TEMP,
    SENSOR_RETURN_TEMP,
    SENSOR_ROOM_TEMPERATURE,
    SENSOR_OUTSIDE_TEMP,
    SENSOR_TARGET_TEMPERATURE
] 