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
from .const import DOMAIN
from .models.sensor import SENSOR_DEFINITIONS

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

    # Create sensor entities from sensor definitions
    sensors = [
        DeWarmteSensorEntityDescription(
            key=key,
            name=definition.name,
            native_unit_of_measurement=definition.unit,
            device_class=definition.device_class,
            state_class=definition.state_class,
            options=["Off", "On"] if definition.device_class == SensorDeviceClass.ENUM else None,
        )
        for key, definition in SENSOR_DEFINITIONS.items()
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
            
        sensor = self.coordinator.data.get(self.entity_description.key)
        if not sensor:
            return None
            
        value = sensor.state.value
        
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