"""Settings models for DeWarmte API."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass
class SettingsGroup:
    """Represents a group of related settings that are updated together."""
    endpoint: str
    keys: List[str]

@dataclass
class WarmWaterRange:
    """Represents a warm water temperature range with time period."""
    order: int
    temperature: float
    period: str  # Format: "HH:MM-HH:MM"

@dataclass
class DeviceOperationSettings:
    """Device operation settings."""
    # Heat curve settings
    heat_curve_mode: str
    heating_kind: str
    heat_curve_s1_outside_temp: float
    heat_curve_s1_target_temp: float
    heat_curve_s2_outside_temp: float
    heat_curve_s2_target_temp: float
    heat_curve_fixed_temperature: float
    heat_curve_use_smart_correction: bool

    # Other settings
    advanced_boost_mode_control: bool
    advanced_thermostat_delay: str
    backup_heating_mode: str
    cooling_thermostat_type: str
    cooling_temperature: float
    cooling_control_mode: str
    cooling_duration: int
    heating_performance_mode: str
    heating_performance_backup_temperature: float
    sound_mode: str
    sound_compressor_power: str
    sound_fan_speed: str
    warm_water_is_scheduled: bool
    warm_water_target_temperature: float
    warm_water_ranges: List[WarmWaterRange]
    version: int
    is_applied: bool

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DeviceOperationSettings":
        """Create settings from API response."""

        return cls(
            # Heat curve settings
            heat_curve_mode=data["heat_curve_mode"],
            heating_kind=data["heating_kind"],
            heat_curve_s1_outside_temp=float(data["heat_curve_s1_outside_temp"]),
            heat_curve_s1_target_temp=float(data["heat_curve_s1_target_temp"]),
            heat_curve_s2_outside_temp=float(data["heat_curve_s2_outside_temp"]),
            heat_curve_s2_target_temp=float(data["heat_curve_s2_target_temp"]),
            heat_curve_fixed_temperature=float(data["heat_curve_fixed_temperature"]) if data["heat_curve_fixed_temperature"] is not None else 0.0,
            heat_curve_use_smart_correction=bool(data["heat_curve_use_smart_correction"]),

            # Other settings
            advanced_boost_mode_control=bool(data["advanced_boost_mode_control"]),
            advanced_thermostat_delay=data["advanced_thermostat_delay"],
            backup_heating_mode=data["backup_heating_mode"],
            cooling_thermostat_type=data["cooling_thermostat_type"],
            cooling_temperature=float(data["cooling_temperature"]),
            cooling_control_mode=data["cooling_control_mode"],
            cooling_duration=int(data["cooling_duration"]),
            heating_performance_mode=data["heating_performance_mode"],
            heating_performance_backup_temperature=float(data["heating_performance_backup_temperature"]),
            sound_mode=data["sound_mode"],
            sound_compressor_power=data["sound_compressor_power"],
            sound_fan_speed=data["sound_fan_speed"],
            warm_water_is_scheduled=bool(data.get("warm_water_is_scheduled", False)),
            warm_water_target_temperature=float(data["warm_water_ranges"][0]["temperature"]) if data.get("warm_water_ranges") and len(data["warm_water_ranges"]) > 0 else 55.0,
            warm_water_ranges=[
                WarmWaterRange(
                    order=range_data.get("order", 0),
                    temperature=float(range_data.get("temperature", 55.0)),
                    period=range_data.get("period", "00:00-00:00")
                )
                for range_data in data.get("warm_water_ranges", [])
            ],
            version=int(data["version"]),
            is_applied=bool(data["is_applied"])
        )

# Define all settings groups
SETTING_GROUPS = {
    "heat_curve": SettingsGroup(
        endpoint="heat-curve",
        keys=["heat_curve_mode", "heating_kind", "heat_curve_s1_outside_temp", 
              "heat_curve_s1_target_temp", "heat_curve_s2_outside_temp", 
              "heat_curve_s2_target_temp", "heat_curve_fixed_temperature", 
              "heat_curve_use_smart_correction"],
    ),
    "heating_performance": SettingsGroup(
        endpoint="heating-performance",
        keys=["heating_performance_mode", "heating_performance_backup_temperature"],
    ),
    "backup_heating": SettingsGroup(
        endpoint="backup-heating",
        keys=["backup_heating_mode"],
    ),
    "sound": SettingsGroup(
        endpoint="sound",
        keys=["sound_mode", "sound_compressor_power", "sound_fan_speed"],
    ),
    "advanced": SettingsGroup(
        endpoint="advanced",
        keys=["advanced_boost_mode_control", "advanced_thermostat_delay"],
    ),
    "cooling": SettingsGroup(
        endpoint="cooling",
        keys=["cooling_thermostat_type", "cooling_control_mode", 
              "cooling_temperature", "cooling_duration"],
    ),
    "warm_water": SettingsGroup(
        endpoint="warm-water",
        keys=["warm_water_is_scheduled", "warm_water_target_temperature"],
    ),
} 