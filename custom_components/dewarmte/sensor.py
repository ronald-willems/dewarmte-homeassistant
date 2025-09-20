"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar, cast, final
from datetime import timedelta, datetime
from decimal import Decimal
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
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.helpers.typing import StateType

from . import _LOGGER, DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.models.status_data import StatusData

# Type variable for sensor values
SensorValueT = TypeVar('SensorValueT', float, int, str, bool)

@dataclass(frozen=True)
class DeWarmteSensorEntityDescription(SensorEntityDescription):
    """Describes DeWarmte sensor entity."""

    # Required fields
    key: str  # The key used to access the sensor value in the coordinator data

    # Optional fields with proper type hints
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit_of_measurement: str | None = None
    device_types: tuple[str, ...] = ("AO", "PT")  # Device types this sensor applies to
    suggested_display_precision: int | None = None

SENSOR_DESCRIPTIONS: tuple[DeWarmteSensorEntityDescription, ...] = (
    # Status sensors
    DeWarmteSensorEntityDescription(
        key="water_flow",
        name="Water Flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_types=("AO",),  # AO-specific: circulation flow for space heating
    ),
    DeWarmteSensorEntityDescription(
        key="supply_temperature",
        name="Supply Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("AO",),  # AO-specific: heating supply temperature
    ),
    DeWarmteSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("AO",),  # AO-specific: outdoor sensor physically connected to AO device
    ),
    DeWarmteSensorEntityDescription(
        key="heat_input",
        name="Heat Input",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_types=("AO", "PT"),  # Common: heat input for both devices
    ),
    DeWarmteSensorEntityDescription(
        key="actual_temperature",
        name="Actual Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("AO",),  # AO-specific: actual heating temperature
    ),
    DeWarmteSensorEntityDescription(
        key="electricity_consumption",
        name="Electricity Consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_types=("AO", "PT"),  # Common: electricity consumption for both
    ),
    DeWarmteSensorEntityDescription(
        key="heat_output",
        name="Heat Output",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_types=("AO", "PT"),  # Common: heat output for both devices
    ),
    DeWarmteSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("AO",),  # AO-specific: heating target temperature
    ),
    DeWarmteSensorEntityDescription(
        key="electric_backup_usage",
        name="Electric Backup Usage",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_types=("AO",),  # AO-specific: backup heating for space heating
    ),
    # Operational status sensors
    DeWarmteSensorEntityDescription(
        key="fault_code",
        name="Fault Code",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        device_types=("AO", "PT"),  # Common: fault codes for both devices
    ),
    # PT device specific sensors (DHW heat pump)
    DeWarmteSensorEntityDescription(
        key="top_boiler_temp",
        name="Top Boiler Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("PT",),  # PT-specific: DHW boiler top temperature
    ),
    DeWarmteSensorEntityDescription(
        key="bottom_boiler_temp",
        name="Bottom Boiler Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_types=("PT",),  # PT-specific: DHW boiler bottom temperature
    ),
)

@final
class DeWarmteSensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SensorEntity):  # type: ignore[override]
    """Representation of a DeWarmte sensor."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteSensorEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteSensorEntityDescription, self.entity_description)
    
    @property
    def native_value(self) -> StateType:  # type: ignore[override]
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        value = getattr(self.coordinator.data, self.dewarmte_description.key, None)
        if value is None:
            return None
        return cast(StateType, value)

@final
class DeWarmteEnergyIntegrationSensor(IntegrationSensor):
    """DeWarmte energy integration sensor that calculates energy from power measurements."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_icon = "mdi:lightning-bolt"
    _attr_has_entity_name = True

    def __init__(self, source_sensor: DeWarmteSensor) -> None:
        """Initialize the energy integration sensor."""
        # Get the polling interval from the coordinator 
        if source_sensor.coordinator.update_interval is None:
            raise ValueError("Coordinator update interval is None")
        polling_interval = source_sensor.coordinator.update_interval.total_seconds()
        
        super().__init__(
            source_sensor.hass,
            source_entity=source_sensor.entity_id,
            name=f"{source_sensor.name} Energy",
            unique_id=f"{source_sensor.unique_id}_energy",
            round_digits=2,
            unit_time=UnitOfTime.HOURS,  # Use proper enum value
            unit_prefix=None,  # kWh without additional prefix
            integration_method="trapezoidal",
            max_sub_interval=timedelta(seconds=polling_interval * 3),
        )
        self._attr_device_info = source_sensor.coordinator.device_info
        self._source_sensor = source_sensor

    @property
    def source_sensor(self) -> DeWarmteSensor:
        """Return the source power sensor."""
        return self._source_sensor

    @callback
    def async_reset(self) -> None:
        """Reset the energy sensor."""
        _LOGGER.debug("%s: Reset energy sensor", self.entity_id)
        self._state = Decimal('0')  # Use Decimal instead of int
        self.async_write_ha_state()

@final
class DeWarmteCoPSensor(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SensorEntity):  # type: ignore[override]
    """Representation of a DeWarmte CoP sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-pump"
    _attr_native_unit_of_measurement = None  # CoP is a ratio, no unit

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        heat_output_sensor: DeWarmteEnergyIntegrationSensor,
        electrical_input_sensor: DeWarmteEnergyIntegrationSensor,
    ) -> None:
        """Initialize the CoP sensor."""
        super().__init__(coordinator)
        self._heat_output_sensor = heat_output_sensor
        self._electrical_input_sensor = electrical_input_sensor
        assert coordinator.device is not None, "Coordinator device must not be None"
        self._attr_unique_id = f"{coordinator.device.device_id}_cop"
        self._attr_name = "CoP"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the current CoP value."""
        if not self.coordinator.data:
            return None

        heat_output = self._heat_output_sensor.native_value
        electrical_input = self._electrical_input_sensor.native_value

        if not heat_output or not electrical_input or electrical_input == 0:
            return 0.0

        try:
            cop = float(heat_output) / float(electrical_input)

            return round(cop, 2)
        except (TypeError, ValueError):
            _LOGGER.error("Failed to calculate CoP from values: heat_output=%s, electrical_input=%s",
                         heat_output, electrical_input)
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return additional state attributes."""
        # Convert Decimal values to float for JSON serialization
        heat_output = self._heat_output_sensor.native_value
        electrical_input = self._electrical_input_sensor.native_value
        
        return {
            # Current values
            "heat_output_kwh": float(heat_output) if heat_output is not None else None,
            "electrical_input_kwh": float(electrical_input) if electrical_input is not None else None,
            "last_updated": datetime.now().isoformat() if self.coordinator.data else None,
        }

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DeWarmte sensors from a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    # Support both a single coordinator and a list for backward compatibility
    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        # Get device type from the coordinator's device
        device_type = coordinator.device.product_id.split()[0] if coordinator.device else "UNKNOWN"  # "AO", "PT", etc.
        
        # Filter sensor descriptions based on device type
        filtered_descriptions = [
            description for description in SENSOR_DESCRIPTIONS
            if device_type in description.device_types
        ]
        
        # Create regular sensors per device with filtered descriptions
        regular_sensors = [DeWarmteSensor(coordinator, description) for description in filtered_descriptions]
        _LOGGER.debug("Adding %d regular sensors for device %s (type: %s)", 
                     len(regular_sensors), 
                     coordinator.device.device_id if coordinator.device else "unknown",
                     device_type)
        async_add_entities(regular_sensors)

        # Wait for sensors to be registered; arbitrary number of seconds
        await asyncio.sleep(3)

        # Then create energy sensors for power sensors per device
        energy_sensors = []
        for sensor in regular_sensors:
            if sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT:
                _LOGGER.debug("Creating energy sensor for power sensor: %s", sensor.name)
                energy_sensor = DeWarmteEnergyIntegrationSensor(sensor)
                energy_sensors.append(energy_sensor)
        
        # Add energy sensors
        if energy_sensors:
            _LOGGER.debug("Adding %d energy sensors for device %s", len(energy_sensors), coordinator.device.device_id if coordinator.device else "unknown")
            async_add_entities(energy_sensors)

            # Wait for energy sensors to be registered
            await asyncio.sleep(3)

            # Find heat output and electrical input energy sensors
            heat_output_sensor = next(
                (s for s in energy_sensors if s.source_sensor.entity_description.key == "heat_output"),
                None
            )
            electrical_input_sensor = next(
                (s for s in energy_sensors if s.source_sensor.entity_description.key == "electricity_consumption"),
                None
            )

            if heat_output_sensor and electrical_input_sensor:
                # Create and add CoP sensor
                cop_sensor = DeWarmteCoPSensor(coordinator, heat_output_sensor, electrical_input_sensor)
                _LOGGER.debug("Adding CoP sensor for device %s", coordinator.device.device_id if coordinator.device else "unknown")
                async_add_entities([cop_sensor])

