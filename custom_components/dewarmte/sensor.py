"""Support for DeWarmte sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .api.models.sensor import SENSOR_DEFINITIONS
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte sensors."""
    coordinator: DeWarmteDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create a sensor entity for each defined sensor
    entities = []
    for sensor_def in SENSOR_DEFINITIONS.values():
        if sensor_def.key in coordinator.data:
            entities.append(
                DeWarmteSensor(
                    coordinator=coordinator,
                    sensor_def=sensor_def,
                )
            )

    async_add_entities(entities)

class DeWarmteSensor(CoordinatorEntity, SensorEntity):
    """Representation of a DeWarmte sensor."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        sensor_def: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_def = sensor_def
        self._attr_unique_id = f"{coordinator.device.device_id}_{sensor_def.key}"
        self._attr_name = sensor_def.name
        self._attr_native_unit_of_measurement = sensor_def.unit
        self._attr_device_class = sensor_def.device_class
        self._attr_state_class = sensor_def.state_class
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and self._sensor_def.key in self.coordinator.data:
            return self.coordinator.data[self._sensor_def.key].value
        return None 