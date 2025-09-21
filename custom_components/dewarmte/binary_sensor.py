"""Binary sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, cast
from functools import cached_property

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

@dataclass(frozen=True)
class DeWarmteBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes DeWarmte binary sensor entity."""

    # Required fields (no default values)
    key: str
    device_types: tuple[str, ...] = ("AO", "PT", "HC")  # Device types this sensor applies to

BINARY_SENSOR_DESCRIPTIONS: tuple[DeWarmteBinarySensorEntityDescription, ...] = (
    DeWarmteBinarySensorEntityDescription(
        key="gas_boiler",
        name="Gas Boiler",
        device_class=BinarySensorDeviceClass.HEAT,
        device_types=("AO",),  # AO-specific: gas boiler backup heating
    ),
    DeWarmteBinarySensorEntityDescription(
        key="thermostat",
        name="Thermostat",
        device_class=BinarySensorDeviceClass.HEAT,
        device_types=("AO",),  # AO-specific: space heating thermostat
    ),
    DeWarmteBinarySensorEntityDescription(
        key="is_on",
        name="Is On",
        device_class=BinarySensorDeviceClass.RUNNING,
        device_types=("AO", "PT"),  # AO/PT only: HC devices don't provide this field
    ),
    DeWarmteBinarySensorEntityDescription(
        key="is_connected",
        name="Is Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        device_types=("AO", "PT"),  # AO/PT only: HC devices don't provide this field
    ),
)

class DeWarmteBinarySensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], BinarySensorEntity): # type: ignore[override]
    """Representation of a DeWarmte binary sensor."""
    _attr_has_entity_name = True

    

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteBinarySensorEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteBinarySensorEntityDescription, self.entity_description)

    @cached_property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if self.coordinator.data:
            value = getattr(self.coordinator.data, self.dewarmte_description.key, None)
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
    coordinators = hass.data[DOMAIN][entry.entry_id]

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        # Get device type from the coordinator's device
        device_type = coordinator.device.product_id.split()[0] if coordinator.device else "UNKNOWN"  # "AO", "PT", etc.
        
        # Filter binary sensor descriptions based on device type
        filtered_descriptions = [
            description for description in BINARY_SENSOR_DESCRIPTIONS
            if device_type in description.device_types
        ]
        
        # Create binary sensors per device with filtered descriptions
        binary_sensors = [
            DeWarmteBinarySensor(coordinator, description) 
            for description in filtered_descriptions
        ]
        _LOGGER.debug("Adding %d binary sensors for device %s (type: %s)", 
                     len(binary_sensors), 
                     coordinator.device.device_id if coordinator.device else "unknown",
                     device_type)
        async_add_entities(binary_sensors) 