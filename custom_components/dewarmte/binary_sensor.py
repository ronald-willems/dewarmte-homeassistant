"""Binary sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import _LOGGER, DeWarmteDataUpdateCoordinator
from .const import DOMAIN

@dataclass
class DeWarmteBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes DeWarmte binary sensor entity."""

    # Required fields (no default values)
    key: str

BINARY_SENSOR_DESCRIPTIONS: tuple[DeWarmteBinarySensorEntityDescription, ...] = (
    DeWarmteBinarySensorEntityDescription(
        key="gas_boiler",
        name="Gas Boiler",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    DeWarmteBinarySensorEntityDescription(
        key="thermostat",
        name="Thermostat",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    DeWarmteBinarySensorEntityDescription(
        key="is_on",
        name="Is On",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    DeWarmteBinarySensorEntityDescription(
        key="is_connected",
        name="Is Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)

class DeWarmteBinarySensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a DeWarmte binary sensor."""
    _attr_has_entity_name = True

    entity_description: DeWarmteBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if self.coordinator.data:
            value = getattr(self.coordinator.data, self.entity_description.key, None)
            # Convert various possible values to boolean
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ["on", "true", "yes", "1", "active"]
            if isinstance(value, (int, float)):
                return value > 0
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DeWarmte binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensors = [
        DeWarmteBinarySensor(coordinator, description) 
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]
    
    _LOGGER.debug("Adding %d binary sensors", len(binary_sensors))
    async_add_entities(binary_sensors) 