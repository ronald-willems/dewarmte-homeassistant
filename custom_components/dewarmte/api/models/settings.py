"""Settings models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum



# Constants
UNIT_CELSIUS = "°C"

@dataclass
class ConnectionSettings():
    """Connection settings for DeWarmte API."""
    username: str
    password: str
    update_interval: int = 300  # 5 minutes in seconds

@dataclass
class PollingSettings():
    """Polling settings for data updates."""
    scan_interval: int = 30  # seconds
    retry_count: int = 3
    retry_delay: int = 5  # seconds

@dataclass
class DeviceSettings():
    """Device-specific settings."""
    name: Optional[str] = None
    area: Optional[str] = None
    disabled: bool = False
    disabled_by: Optional[str] = None
    entity_category: Optional[str] = None

@dataclass
class IntegrationSettings():
    """Main settings container for the integration."""
    connection: ConnectionSettings
    polling: PollingSettings
    devices: Dict[str, DeviceSettings]
    extra_settings: Dict[str, Any] = None

class ThermostatDelay(str, Enum):
    """Thermostat delay settings."""
    MIN = "min"
    MED = "med"
    MAX = "max"

class BackupHeatingMode(str, Enum):
    """Backup heating mode settings."""
    AUTO = "auto"
    ECO = "eco"
    COMFORT = "comfort"

class CoolingThermostatType(str, Enum):
    """Cooling thermostat type settings."""
    HEATING_ONLY = "heating_only"
    HEATING_AND_COOLING = "heating_and_cooling"

class CoolingControlMode(str, Enum):
    """Cooling control mode settings."""
    THERMOSTAT = "thermostat"
    MANUAL = "manual"

class HeatCurveMode(str, Enum):
    """Heat curve mode settings."""
    WEATHER = "weather"
    FIXED = "fixed"

class HeatingKind(str, Enum):
    """Heating kind settings."""
    CUSTOM = "custom"
    FLOOR = "floor"
    RADIATOR = "radiator"
    BOTH = "both"

class HeatingPerformanceMode(str, Enum):
    """Heating performance mode settings."""
    AUTO = "auto"
    POMP_AO_ONLY = "pomp_ao_only"
    POMP_AO_AND_BACKUP = "pomp_ao_and_backup"
    BACKUP_ONLY = "backup_only"

class SoundMode(str, Enum):
    """Sound mode settings."""
    NORMAL = "normal"
    SILENT = "silent"

class PowerLevel(str, Enum):
    """Power level settings."""
    MIN = "min"
    MED = "med"
    MAX = "max"

@dataclass
class WarmWaterRange():
    """Warm water range settings."""
    order: int
    temperature: float
    period: str

@dataclass
class HeatCurveSettings():
    """Heat curve settings."""
    mode: HeatCurveMode
    heating_kind: HeatingKind
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
class DeviceOperationSettings():
    """Device operation settings."""
    advanced_boost_mode_control: bool
    advanced_thermostat_delay: ThermostatDelay
    backup_heating_mode: BackupHeatingMode
    cooling_thermostat_type: CoolingThermostatType
    cooling_temperature: float
    cooling_control_mode: CoolingControlMode
    cooling_duration: int
    heat_curve: HeatCurveSettings
    heating_performance_mode: HeatingPerformanceMode
    heating_performance_backup_temperature: float
    sound_mode: SoundMode
    sound_compressor_power: PowerLevel
    sound_fan_speed: PowerLevel
    warm_water_is_scheduled: bool
    warm_water_ranges: List[WarmWaterRange]
    version: int
    is_applied: bool

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DeviceOperationSettings":
        """Create settings from API response."""
        heat_curve = HeatCurveSettings(
            mode=HeatCurveMode(data["heat_curve_mode"]),
            heating_kind=HeatingKind(data["heating_kind"]),
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
            advanced_thermostat_delay=ThermostatDelay(data["advanced_thermostat_delay"]),
            backup_heating_mode=BackupHeatingMode(data["backup_heating_mode"]),
            cooling_thermostat_type=CoolingThermostatType(data["cooling_thermostat_type"]),
            cooling_temperature=float(data["cooling_temperature"]),
            cooling_control_mode=CoolingControlMode(data["cooling_control_mode"]),
            cooling_duration=int(data["cooling_duration"]),
            heat_curve=heat_curve,
            heating_performance_mode=HeatingPerformanceMode(data["heating_performance_mode"]),
            heating_performance_backup_temperature=float(data["heating_performance_backup_temperature"]),
            sound_mode=SoundMode(data["sound_mode"]),
            sound_compressor_power=PowerLevel(data["sound_compressor_power"]),
            sound_fan_speed=PowerLevel(data["sound_fan_speed"]),
            warm_water_is_scheduled=bool(data["warm_water_is_scheduled"]),
            warm_water_ranges=warm_water_ranges,
            version=int(data["version"]),
            is_applied=bool(data["is_applied"])
        ) 