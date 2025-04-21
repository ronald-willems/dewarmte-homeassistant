"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from datetime import timedelta
import asyncio

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
from homeassistant.core import HomeAssistant, callback
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

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, source_sensor: DeWarmteSensor) -> None:
        """Initialize the energy integration sensor."""
        # Get the polling interval from the coordinator 
        polling_interval = source_sensor.coordinator.update_interval.total_seconds()
        
        super().__init__(
            source_entity=source_sensor.entity_id,
            name=f"{source_sensor.name} Energy",
            unique_id=f"{source_sensor.unique_id}_energy",
            round_digits=2,
            unit_time="h",
            unit_prefix=None,  # kWh without additional prefix
            integration_method="trapezoidal",
            max_sub_interval=timedelta(seconds=polling_interval * 2),
        )
        self._attr_device_info = source_sensor.coordinator.device_info

    @callback
    def async_reset(self) -> None:
        """Reset the energy sensor."""
        _LOGGER.debug("%s: Reset energy sensor", self.entity_id)
        self._state = 0
        self.async_write_ha_state()



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DeWarmte sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # First create regular sensors
    regular_sensors = [DeWarmteSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    _LOGGER.debug("Adding %d regular sensors", len(regular_sensors))
    async_add_entities(regular_sensors)

    # Wait for sensors to be registered; arbitrary number of seconds
    await asyncio.sleep(5)

    # Then create energy sensors for power sensors
    energy_sensors = []
    for sensor in regular_sensors:
        if sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT:
            _LOGGER.debug("Creating energy sensor for power sensor: %s", sensor.name)
            energy_sensor = DeWarmteEnergyIntegrationSensor(sensor)
            energy_sensors.append(energy_sensor)
    
    # Add energy sensors
    if energy_sensors:
        _LOGGER.debug("Adding %d energy sensors", len(energy_sensors))
        async_add_entities(energy_sensors)

