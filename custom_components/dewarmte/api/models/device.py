"""Device model for DeWarmte."""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DeviceInfo:
    """Device information."""
    name: str
    manufacturer: str = "DeWarmte"
    model: str = "AO"
    sw_version: str = "1.0.0"
    hw_version: str = "1.0.0"

@dataclass
class Device:
    """Device model."""
    device_id: str
    product_id: str
    access_token: str
    name: str | None = None
    online: bool = False
    _info: Optional[DeviceInfo] = None

    @property
    def is_online(self) -> bool:
        """Return if the device is online."""
        return self.online

    @property
    def info(self) -> DeviceInfo:
        """Return device information."""
        if not self._info:
            self._info = DeviceInfo(
                name=self.name or f"DeWarmte {self.product_id}",
            )
        return self._info

    @classmethod
    def from_api_response(cls, device_id: str, product_id: str, access_token: str, name: Optional[str] = None) -> "Device":
        """Create a device from an API response."""
        return cls(
            device_id=device_id,
            product_id=product_id,
            access_token=access_token,
            name=name,
            online=True  # We assume it's online if we can get the data
        ) 