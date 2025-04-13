"""Settings models for DeWarmte API."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .base import BaseModel

@dataclass
class WarmWaterRange(BaseModel):
    """Warm water range settings."""
    order: int
    temperature: float
    period: str

@dataclass
class HeatCurveSettings(BaseModel):
    """Heat curve settings."""
    mode: str
    heating_kind: str
    s1_outside_temp: float
    s1_target_temp: float
    s2_outside_temp: float
    s2_target_temp: float
    fixed_temperature: float
    use_smart_correction: bool

    @property
    def s1_outside_temp_celsius(self) -> float:
        """Get S1 outside temperature in Celsius."""
        return self.s1_outside_temp

    @property
    def s1_target_temp_celsius(self) -> float:
        """Get S1 target temperature in Celsius."""
        return self.s1_target_temp

    @property
    def s2_outside_temp_celsius(self) -> float:
        """Get S2 outside temperature in Celsius."""
        return self.s2_outside_temp

    @property
    def s2_target_temp_celsius(self) -> float:
        """Get S2 target temperature in Celsius."""
        return self.s2_target_temp

    @property
    def fixed_temperature_celsius(self) -> float:
        """Get fixed temperature in Celsius."""
        return self.fixed_temperature

@dataclass
class DeviceOperationSettings(BaseModel):
    """Device operation settings."""
    advanced_boost_mode_control: bool
    advanced_thermostat_delay: str
    backup_heating_mode: str
    cooling_thermostat_type: str
    cooling_temperature: float
    cooling_control_mode: str
    cooling_duration: int
    heat_curve: HeatCurveSettings
    heating_performance_mode: str
    heating_performance_backup_temperature: float
    sound_mode: str
    sound_compressor_power: str
    sound_fan_speed: str
    warm_water_is_scheduled: bool
    warm_water_ranges: List[WarmWaterRange]
    version: int
    is_applied: bool

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DeviceOperationSettings":
        """Create settings from API response."""
        heat_curve = HeatCurveSettings(
            mode=data["heat_curve_mode"],
            heating_kind=data["heating_kind"],
            s1_outside_temp=float(data["heat_curve_s1_outside_temp"]),
            s1_target_temp=float(data["heat_curve_s1_target_temp"]),
            s2_outside_temp=float(data["heat_curve_s2_outside_temp"]),
            s2_target_temp=float(data["heat_curve_s2_target_temp"]),
            fixed_temperature=float(data["heat_curve_fixed_temperature"]),
            use_smart_correction=bool(data["heat_curve_use_smart_correction"])
        )

        warm_water_ranges = [
            WarmWaterRange(**range_data)
            for range_data in data.get("warm_water_ranges", [])
        ]

        return cls(
            advanced_boost_mode_control=bool(data["advanced_boost_mode_control"]),
            advanced_thermostat_delay=data["advanced_thermostat_delay"],
            backup_heating_mode=data["backup_heating_mode"],
            cooling_thermostat_type=data["cooling_thermostat_type"],
            cooling_temperature=float(data["cooling_temperature"]),
            cooling_control_mode=data["cooling_control_mode"],
            cooling_duration=int(data["cooling_duration"]),
            heat_curve=heat_curve,
            heating_performance_mode=data["heating_performance_mode"],
            heating_performance_backup_temperature=float(data["heating_performance_backup_temperature"]),
            sound_mode=data["sound_mode"],
            sound_compressor_power=data["sound_compressor_power"],
            sound_fan_speed=data["sound_fan_speed"],
            warm_water_is_scheduled=bool(data["warm_water_is_scheduled"]),
            warm_water_ranges=warm_water_ranges,
            version=int(data["version"]),
            is_applied=bool(data["is_applied"])
        ) 