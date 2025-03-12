"""Base models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class BaseModel:
    """Base model for all DeWarmte models."""
    pass

@dataclass
class ValueUnit:
    """Base model for values with units."""
    value: Any
    unit: Optional[str] = None 