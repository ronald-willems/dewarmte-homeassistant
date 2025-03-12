"""Device models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Dict, Optional

from . import BaseModel, ValueUnit
from .sensor import SensorDefinition

@dataclass
class DeviceInfo(BaseModel):
    """Device information model."""
    name: str
    model: str
    manufacturer: str = "DeWarmte"
    sw_version: Optional[str] = None
    hw_version: Optional[str] = None

@dataclass
class DeviceState(BaseModel):
    """Device state model."""
    online: bool
    last_update: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None

@dataclass
class DeviceSensor(BaseModel):
    """Device sensor model."""
    definition: SensorDefinition
    state: ValueUnit

@dataclass
class Device(BaseModel):
    """DeWarmte device model."""
    device_id: str
    info: DeviceInfo
    state: DeviceState
    sensors: Dict[str, DeviceSensor] 