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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
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