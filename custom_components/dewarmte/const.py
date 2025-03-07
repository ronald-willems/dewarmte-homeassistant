"""Constants for the DeWarmte integration."""
DOMAIN = "dewarmte"

# Configuration
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes

# Sensor types
SENSOR_SUPPLY_TEMPERATURE = "supply_temperature"  # Aanvoer temperatuur
SENSOR_RETURN_TEMPERATURE = "return_temperature"  # Retour temperatuur
SENSOR_ROOM_TEMPERATURE = "room_temperature"      # Kamer temperatuur
SENSOR_OUTSIDE_TEMPERATURE = "outside_temperature"  # Buiten temperatuur
SENSOR_TARGET_TEMPERATURE = "target_temperature"  # Gewenste temperatuur
SENSOR_HEAT_DEMAND = "heat_demand"               # Warmtevraag (%)
SENSOR_VALVE_POSITION = "valve_position"         # Klepstand (%)
SENSOR_STATUS = "status"                         # System status

# Sensor display names
SENSOR_NAMES = {
    SENSOR_SUPPLY_TEMPERATURE: "Supply Temperature",
    SENSOR_RETURN_TEMPERATURE: "Return Temperature",
    SENSOR_ROOM_TEMPERATURE: "Room Temperature",
    SENSOR_OUTSIDE_TEMPERATURE: "Outside Temperature",
    SENSOR_TARGET_TEMPERATURE: "Target Temperature",
    SENSOR_HEAT_DEMAND: "Heat Demand",
    SENSOR_VALVE_POSITION: "Valve Position",
    SENSOR_STATUS: "Status"
}

# Sensor classes
PERCENTAGE_SENSORS = [SENSOR_HEAT_DEMAND, SENSOR_VALVE_POSITION]
TEMPERATURE_SENSORS = [
    SENSOR_SUPPLY_TEMPERATURE,
    SENSOR_RETURN_TEMPERATURE,
    SENSOR_ROOM_TEMPERATURE,
    SENSOR_OUTSIDE_TEMPERATURE,
    SENSOR_TARGET_TEMPERATURE
] 