"""Status data models for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

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
        status = cls()
        status.update_from_dict(data)
        return status

    def update_from_dict(self, data: dict) -> None:
        """Incrementally update fields."""
        issues = list(self.invalid_fields)

        for key, raw in data.items():
            if key == "invalid_fields":
                continue

            annotation = StatusData.__annotations__.get(key)
            if annotation is None:
                continue

            if raw in ("", None):
                issues.append(f"{key}={raw!r} (missing)")
                setattr(self, key, None)
                continue

            try:
                if _annotation_includes(annotation, bool):
                    value = _coerce_bool(raw)
                elif _annotation_includes(annotation, int):
                    value = _coerce_int(raw)
                elif _annotation_includes(annotation, float):
                    value = _coerce_float(raw)
                else:
                    value = raw
            except (TypeError, ValueError):
                issues.append(f"{key}={raw!r} (invalid)")
                value = None

            setattr(self, key, value)

        self.invalid_fields = tuple(issues)


def _annotation_includes(annotation: Any, target_type: type) -> bool:
    if annotation is target_type:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    return any(_annotation_includes(arg, target_type) for arg in get_args(annotation))


def _coerce_float(value: Any) -> float:
    return float(value)


def _coerce_int(value: Any) -> int:
    return int(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "active"}:
            return True
        if normalized in {"false", "0", "no", "off", "inactive"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    raise ValueError("Invalid boolean value")