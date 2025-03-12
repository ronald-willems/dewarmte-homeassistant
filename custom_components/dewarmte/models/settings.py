"""Settings models for DeWarmte integration."""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from . import BaseModel

@dataclass
class ConnectionSettings(BaseModel):
    """Connection settings for DeWarmte API."""
    username: str
    password: str
    update_interval: int = 300  # 5 minutes in seconds

@dataclass
class PollingSettings(BaseModel):
    """Polling settings for data updates."""
    scan_interval: int = 30  # seconds
    retry_count: int = 3
    retry_delay: int = 5  # seconds

@dataclass
class DeviceSettings(BaseModel):
    """Device-specific settings."""
    name: Optional[str] = None
    area: Optional[str] = None
    disabled: bool = False
    disabled_by: Optional[str] = None
    entity_category: Optional[str] = None

@dataclass
class IntegrationSettings(BaseModel):
    """Main settings container for the integration."""
    connection: ConnectionSettings
    polling: PollingSettings
    devices: Dict[str, DeviceSettings]
    extra_settings: Dict[str, Any] = None 