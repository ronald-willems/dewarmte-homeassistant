"""Base models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class BaseModel:
    """Base model for all DeWarmte models."""
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "BaseModel":
        """Create a model instance from API response data."""
        return cls(**data)

@dataclass
class ValueUnit:
    """Base model for values with units."""
    value: Any
    unit: Optional[str] = None 