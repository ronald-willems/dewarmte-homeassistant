"""Climate platform for DeWarmte integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast, final

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.models.settings import WarmWaterRange

_LOGGER = logging.getLogger(__name__)

# Warm water temperature constants
MIN_WARM_WATER_TEMP = 40.0
MAX_WARM_WATER_TEMP = 70.0
DEFAULT_WARM_WATER_TEMP = 55.0

@dataclass(frozen=True)
class DeWarmteClimateEntityDescription(ClimateEntityDescription):
    """Class describing DeWarmte climate entities."""
    device_types: tuple[str, ...] = ("PT", "HC")  # Device types this climate applies to

CLIMATE_DESCRIPTIONS = {
    "warm_water": DeWarmteClimateEntityDescription(
        key="warm_water",
        name="Warm Water",
        device_types=("PT", "HC"),  # PT/HC-specific: warm water control for heat pumps
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte climate platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setting up DeWarmte climate platform")

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        # Filter climate descriptions by device type
        filtered_descriptions = [
            description for description in CLIMATE_DESCRIPTIONS.values()
            if coordinator.device.device_type in description.device_types
        ]
        
        climates = [
            DeWarmteClimateEntity(coordinator, description)
            for description in filtered_descriptions
        ]
        
        _LOGGER.debug("Adding %d climate entities for device %s (type: %s)",
                     len(climates),
                     coordinator.device.device_id if coordinator.device else "unknown",
                     coordinator.device.device_type)
        
        if climates:
            async_add_entities(climates)

@final
class DeWarmteClimateEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], ClimateEntity):
    """Representation of a DeWarmte climate entity."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["eco", "comfort", "boost", "away"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_WARM_WATER_TEMP
    _attr_max_temp = MAX_WARM_WATER_TEMP
    _attr_target_temperature_step = 1.0

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteClimateEntityDescription,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteClimateEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteClimateEntityDescription, self.entity_description)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.coordinator.data:
            return None
        
        # Use top boiler temperature as current temperature for warm water
        if hasattr(self.coordinator.data, 'top_boiler_temp'):
            return self.coordinator.data.top_boiler_temp
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return DEFAULT_WARM_WATER_TEMP
        
        # Get current warm water ranges from settings
        settings = self.coordinator._cached_settings
        if hasattr(settings, 'warm_water_ranges') and settings.warm_water_ranges:
            # Return the temperature from the first range
            return settings.warm_water_ranges[0].temperature
        
        return DEFAULT_WARM_WATER_TEMP

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return HVACMode.OFF
        
        settings = self.coordinator._cached_settings
        if hasattr(settings, 'warm_water_is_scheduled') and settings.warm_water_is_scheduled:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        target_temp = self.target_temperature
        if target_temp is None:
            return "comfort"
        
        if target_temp <= 45:
            return "eco"
        elif target_temp <= 55:
            return "comfort"
        elif target_temp <= 65:
            return "boost"
        else:
            return "away"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (scheduled vs manual)."""
        if hvac_mode == HVACMode.HEAT:
            # Enable scheduled mode with default ranges
            await self._set_scheduled_mode_with_default_ranges()
        elif hvac_mode == HVACMode.OFF:
            # Disable scheduled mode (manual mode)
            await self.coordinator.api.async_update_operation_settings(
                self.coordinator.device, "warm_water_is_scheduled", False
            )
        
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        target_temp = kwargs.get("temperature")
        if target_temp is None:
            return
        
        # If in scheduled mode, update the ranges
        if self.hvac_mode == HVACMode.HEAT:
            await self._update_warm_water_ranges_with_temperature(target_temp)
        else:
            # If in manual mode, create a single 24/7 range
            await self._create_single_range_mode(target_temp)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        temp_map = {
            "eco": 45.0,
            "comfort": 55.0,
            "boost": 65.0,
            "away": 40.0,
        }
        
        target_temp = temp_map.get(preset_mode, 55.0)
        await self.async_set_temperature(temperature=target_temp)

    async def _set_scheduled_mode_with_default_ranges(self) -> None:
        """Set scheduled mode with at least 2 ranges as required by API."""
        current_temp = self.target_temperature or DEFAULT_WARM_WATER_TEMP
        
        # Create default schedule: day (comfort) and night (eco)
        ranges = [
            WarmWaterRange(
                order=0,
                temperature=current_temp,
                period="06:00-22:00"  # Day time
            ),
            WarmWaterRange(
                order=1, 
                temperature=max(MIN_WARM_WATER_TEMP, current_temp - 10),  # Night time (eco)
                period="22:00-06:00"
            )
        ]
        
        await self._update_warm_water_ranges(ranges)

    async def _update_warm_water_ranges_with_temperature(self, target_temp: float) -> None:
        """Update warm water ranges with new temperature while keeping schedule structure."""
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return
        
        settings = self.coordinator._cached_settings
        if not hasattr(settings, 'warm_water_ranges') or not settings.warm_water_ranges:
            # No existing ranges, create default schedule
            await self._set_scheduled_mode_with_default_ranges()
            return
        
        # Update existing ranges with new temperature
        ranges = []
        for i, range_data in enumerate(settings.warm_water_ranges):
            ranges.append(WarmWaterRange(
                order=i,
                temperature=target_temp,
                period=range_data.period
            ))
        
        await self._update_warm_water_ranges(ranges)

    async def _create_single_range_mode(self, target_temp: float) -> None:
        """Create single 24/7 range for manual mode."""
        ranges = [
            WarmWaterRange(
                order=0,
                temperature=target_temp,
                period="00:00-00:00"  # 24/7 period
            )
        ]
        
        await self._update_warm_water_ranges(ranges)

    async def _update_warm_water_ranges(self, ranges: list[WarmWaterRange]) -> None:
        """Update warm water ranges via API."""
        # First enable scheduled mode
        await self.coordinator.api.async_update_operation_settings(
            self.coordinator.device, "warm_water_is_scheduled", True
        )
        
        # Then update the ranges
        url = f"{self.coordinator.api._base_url}/customer/products/{self.coordinator.device.device_id}/settings/warm-water/"
        
        # Convert WarmWaterRange objects to dicts for API
        ranges_dict = [
            {
                "order": range_obj.order,
                "temperature": range_obj.temperature,
                "period": range_obj.period
            }
            for range_obj in ranges
        ]
        
        update_data = {
            "warm_water_is_scheduled": True,
            "warm_water_ranges": ranges_dict
        }
        
        _LOGGER.debug("Updating warm water ranges: %s", update_data)
        
        try:
            response = await self.coordinator.api._request_with_retry("POST", url, json=update_data)
            if response is None:
                raise Exception("API request failed: no response")
            
            _LOGGER.debug("Successfully updated warm water ranges")
        except Exception as e:
            _LOGGER.error("Error updating warm water ranges: %s", e)
            raise
