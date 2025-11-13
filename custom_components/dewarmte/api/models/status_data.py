"""Status data models for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

RawValue = Any

@dataclass
class StatusData:
    """Status data model from API."""
    water_flow: float | None = None
    supply_temperature: float | None = None
    outdoor_temperature: float | None = None
    heat_input: float | None = None
    actual_temperature: float | None = None
    electricity_consumption: float | None = None
    heat_output: float | None = None
    gas_boiler: bool | None = None
    thermostat: bool | None = None
    target_temperature: float | None = None
    electric_backup_usage: float | None = None
    is_on: bool | None = None
    fault_code: int | None = None
    is_connected: bool | None = None

    # PT/HC device specific fields (DHW heat pump)
    top_boiler_temp: float | None = None
    bottom_boiler_temp: float | None = None

    # bookkeeping of fields that could not be parsed
    invalid_fields: tuple[str, ...] = field(default_factory=tuple, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "StatusData":
        """Create StatusData from dictionary."""
        issues: list[str] = []

        def _has_key(key: str) -> bool:
            return key in data

        def _mark_issue(key: str, value: RawValue, reason: str) -> None:
            issues.append(f"{key}={value!r} ({reason})")

        def _coerce_float(key: str) -> float | None:
            if not _has_key(key):
                return None
            raw = data.get(key)
            if raw in ("", None):
                _mark_issue(key, raw, "missing")
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                _mark_issue(key, raw, "invalid")
                return None

        def _coerce_int(key: str) -> int | None:
            if not _has_key(key):
                return None
            raw = data.get(key)
            if raw in ("", None):
                _mark_issue(key, raw, "missing")
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                _mark_issue(key, raw, "invalid")
                return None

        def _coerce_bool(key: str) -> bool | None:
            if not _has_key(key):
                return None
            raw = data.get(key)
            if raw in ("", None):
                _mark_issue(key, raw, "missing")
                return None
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                normalized = raw.strip().lower()
                if normalized in {"true", "1", "yes", "on", "active"}:
                    return True
                if normalized in {"false", "0", "no", "off", "inactive"}:
                    return False
            if isinstance(raw, (int, float)):
                return bool(raw)
            _mark_issue(key, raw, "invalid")
            return None

        status = cls(
            water_flow=_coerce_float("water_flow"),
            supply_temperature=_coerce_float("supply_temperature"),
            outdoor_temperature=_coerce_float("outdoor_temperature"),
            heat_input=_coerce_float("heat_input"),
            actual_temperature=_coerce_float("actual_temperature"),
            electricity_consumption=_coerce_float("electricity_consumption"),
            heat_output=_coerce_float("heat_output"),
            gas_boiler=_coerce_bool("gas_boiler"),
            thermostat=_coerce_bool("thermostat"),
            target_temperature=_coerce_float("target_temperature"),
            electric_backup_usage=_coerce_float("electric_backup_usage"),
            is_on=_coerce_bool("is_on"),
            fault_code=_coerce_int("fault_code"),
            is_connected=_coerce_bool("is_connected"),
            top_boiler_temp=_coerce_float("top_boiler_temp"),
            bottom_boiler_temp=_coerce_float("bottom_boiler_temp"),
            invalid_fields=tuple(issues),
        )

        return status