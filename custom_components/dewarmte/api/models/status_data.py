"""Status data models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class StatusData:
    """Status data model from API."""
    water_flow: float
    supply_temperature: float
    outdoor_temperature: float
    heat_input: float
    actual_temperature: float
    electricity_consumption: float
    heat_output: float
    gas_boiler: bool
    thermostat: bool
    target_temperature: float
    electric_backup_usage: float
    is_on: bool
    fault_code: int
    is_connected: bool

    @classmethod
    def from_dict(cls, data: dict) -> "StatusData":
        """Create StatusData from dictionary."""
        return cls(
            water_flow=float(data.get("water_flow", 0)),
            supply_temperature=float(data.get("supply_temperature", 0)),
            outdoor_temperature=float(data.get("outdoor_temperature", 0)),
            heat_input=float(data.get("heat_input", 0)),
            actual_temperature=float(data.get("actual_temperature", 0)),
            electricity_consumption=float(data.get("electricity_consumption", 0)),
            heat_output=float(data.get("heat_output", 0)),
            gas_boiler=bool(data.get("gas_boiler", False)),
            thermostat=bool(data.get("thermostat", False)),
            target_temperature=float(data.get("target_temperature", 0)),
            electric_backup_usage=float(data.get("electric_backup_usage", 0)),
            is_on=bool(data.get("is_on", False)),
            fault_code=int(data.get("fault_code", 0)),
            is_connected=bool(data.get("is_connected", False))
        ) 