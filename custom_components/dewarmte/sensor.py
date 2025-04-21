"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.helpers.typing import StateType

from . import _LOGGER, DeWarmteDataUpdateCoordinator
from .const import DOMAIN

@dataclass
class DeWarmteSensorEntityDescription(SensorEntityDescription):
    """Describes DeWarmte sensor entity."""

    # Required fields (no default values)
    key: str
  #  var_name: str

    # Optional fields (with default values)
#    device_class: SensorDeviceClass | None = None
#    state_class: SensorStateClass | None = None
#    suggested_unit_of_measurement: str | None = None
#    suggested_display_precision: int | None = None

SENSOR_DESCRIPTIONS: tuple[DeWarmteSensorEntityDescription, ...] = (
    # Status sensors
    DeWarmteSensorEntityDescription(
        key="water_flow",
        name="Water Flow",
       # var_name="water_flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
    ),
    DeWarmteSensorEntityDescription(
        key="supply_temperature",
        name="Supply Temperature",
     #   var_name="supply_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    DeWarmteSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
     #   var_name="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    DeWarmteSensorEntityDescription(
        key="heat_input",
        name="Heat Input",
     #   var_name="heat_input",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    DeWarmteSensorEntityDescription(
        key="actual_temperature",
        name="Actual Temperature",
     #   var_name="actual_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    DeWarmteSensorEntityDescription(
        key="electricity_consumption",
        name="Electricity Consumption",
     #   var_name="electricity_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    DeWarmteSensorEntityDescription(
        key="heat_output",
        name="Heat Output",
     #   var_name="heat_output",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    DeWarmteSensorEntityDescription(
        key="gas_boiler",
        name="Gas Boiler",
     #   var_name="gas_boiler",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    DeWarmteSensorEntityDescription(
        key="thermostat",
        name="Thermostat",
     #   var_name="thermostat",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    DeWarmteSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
     #   var_name="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    DeWarmteSensorEntityDescription(
        key="electric_backup_usage",
        name="Electric Backup Usage",
     #   var_name="electric_backup_usage",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    # Operational status sensors
    DeWarmteSensorEntityDescription(
        key="is_on",
        name="Is On",
     #   var_name="is_on",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    DeWarmteSensorEntityDescription(
        key="fault_code",
        name="Fault Code",
     #   var_name="fault_code",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
    ),
    DeWarmteSensorEntityDescription(
        key="is_connected",
        name="Is Connected",
     #   var_name="is_connected",
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        native_unit_of_measurement=None,
    ),
)

class DeWarmteSensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SensorEntity):
    """Representation of a DeWarmte sensor."""
    _attr_has_entity_name = True

    entity_description: DeWarmteSensorEntityDescription

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
        self._attr_device_info = coordinator.device_info
    
        
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return getattr(self.coordinator.data, self.entity_description.key, None)
        return None
    



class DeWarmteEnergyIntegrationSensor(IntegrationSensor):
    """DeWarmte energy integration sensor that calculates energy from power measurements."""

    def __init__(self, source_sensor: DeWarmteSensor) -> None:
        """Initialize the energy integration sensor."""
        # Get the polling interval from the coordinator 
        polling_interval = source_sensor.coordinator.update_interval.total_seconds()
        
        # Format the product_id for use in entity_id (replace spaces and hyphens with underscores)
        formatted_id = source_sensor.coordinator.device.product_id.lower().replace(" ", "_").replace("-", "_")
        source_entity_id = f"sensor.dewarmte_{formatted_id}_{source_sensor.entity_description.key}"
        
        _LOGGER.debug(
            "Initializing energy integration sensor for %s with unique_id %s and source_entity %s",
            source_sensor.name,
            f"{source_sensor.unique_id}_energy",
            source_entity_id
        )
        
        super().__init__(
            name=f"{source_sensor.name} Energy",
            source_entity=source_entity_id,
            unit_prefix="k",
            round_digits=2,
            unit_time="h",
            integration_method="trapezoidal",
            unique_id=f"{source_sensor.unique_id}_energy",
            max_sub_interval=timedelta(seconds=polling_interval * 2),
        )
        self._attr_device_info = source_sensor.coordinator.device_info



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DeWarmte sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Add  sensors
    sensors = []
    for description in SENSOR_DESCRIPTIONS:
        current_sensor = DeWarmteSensor(coordinator, description)
        sensors.append(current_sensor)
        
        # If this is a power sensor, create an energy sensor for it
        # TODO: Add support for other units of measurement. Not working yet.
        if current_sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT:
            sensors.append(
                DeWarmteEnergyIntegrationSensor(current_sensor)
            )

    async_add_entities(sensors)

