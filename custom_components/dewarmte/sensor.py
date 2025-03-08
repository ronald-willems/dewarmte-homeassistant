"""Support for DeWarmte sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DeWarmteDataUpdateCoordinator
from .const import (
    DOMAIN,
    SENSOR_WATER_FLOW,
    SENSOR_SUPPLY_TEMP,
    SENSOR_OUTSIDE_TEMP,
    SENSOR_HEAT_INPUT,
    SENSOR_RETURN_TEMP,
    SENSOR_ELEC_CONSUMP,
    SENSOR_PUMP_AO_STATE,
    SENSOR_HEAT_OUTPUT,
    SENSOR_BOILER_STATE,
    SENSOR_THERMOSTAT_STATE,
    SENSOR_TOP_TEMP,
    SENSOR_BOTTOM_TEMP,
    SENSOR_HEAT_OUTPUT_PUMP_T,
    SENSOR_ELEC_CONSUMP_PUMP_T,
    SENSOR_PUMP_T_STATE,
    SENSOR_PUMP_T_HEATER_STATE,
)

@dataclass
class DeWarmteSensorEntityDescription(SensorEntityDescription):
    """Class describing DeWarmte sensor entities."""

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte sensors from config entry."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Define all sensor types
    sensors = [
        DeWarmteSensorEntityDescription(
            key=SENSOR_WATER_FLOW,
            name="Water Flow",
            native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_SUPPLY_TEMP,
            name="Supply Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_OUTSIDE_TEMP,
            name="Outside Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_HEAT_INPUT,
            name="Heat Input",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_RETURN_TEMP,
            name="Return Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_ELEC_CONSUMP,
            name="Electricity Consumption",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_PUMP_AO_STATE,
            name="Pump AO State",
            device_class=SensorDeviceClass.ENUM,
            options=["Off", "On"],
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_HEAT_OUTPUT,
            name="Heat Output",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_BOILER_STATE,
            name="Boiler State",
            device_class=SensorDeviceClass.ENUM,
            options=["Off", "On"],
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_THERMOSTAT_STATE,
            name="Thermostat State",
            device_class=SensorDeviceClass.ENUM,
            options=["Off", "On"],
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_TOP_TEMP,
            name="Top Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_BOTTOM_TEMP,
            name="Bottom Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_HEAT_OUTPUT_PUMP_T,
            name="Heat Output Pump T",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_ELEC_CONSUMP_PUMP_T,
            name="Electricity Consumption Pump T",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_PUMP_T_STATE,
            name="Pump T State",
            device_class=SensorDeviceClass.ENUM,
            options=["Off", "On"],
        ),
        DeWarmteSensorEntityDescription(
            key=SENSOR_PUMP_T_HEATER_STATE,
            name="Pump T Heater State",
            device_class=SensorDeviceClass.ENUM,
            options=["Off", "On"],
        ),
    ]

    async_add_entities(
        DeWarmteSensor(coordinator, description)
        for description in sensors
    )

class DeWarmteSensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SensorEntity):
    """Representation of a DeWarmte sensor."""

    entity_description: DeWarmteSensorEntityDescription

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data.get(self.entity_description.key)
        if not data:
            return None
            
        value = data.get("value")
        
        # Convert boolean states to On/Off
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            return "On" if value == 1 else "Off"
            
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.key in self.coordinator.data
        ) 