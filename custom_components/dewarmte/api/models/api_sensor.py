"""API sensor model for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass
class ApiSensor:
    """Basic representation of a sensor from the API."""
    key: str
    value: Any 