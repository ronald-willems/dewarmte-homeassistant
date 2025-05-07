"""Device model for DeWarmte."""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DwDeviceInfo:
    """Device information."""
    name: str
    manufacturer: str = "DeWarmte"
    model: str = "AO"
    sw_version: str = ""
    hw_version: str = ""

@dataclass
class Device:
    """Device model."""
    device_id: str
    product_id: str
    access_token: str
    name: str | None = None
    online: bool = False
    supports_cooling: bool = False
    _info: Optional[DwDeviceInfo] = None

    @property
    def is_online(self) -> bool:
        """Return if the device is online."""
        return self.online

    @property
    def info(self) -> DwDeviceInfo:
        """Return device information."""
        if not self._info:
            self._info = DwDeviceInfo(
                name=self.name or f"DeWarmte {self.product_id}",
            )
        return self._info

    @classmethod
    def from_api_response(cls, device_id: str, product_id: str, access_token: str, name: Optional[str] = None, supports_cooling: bool = False) -> "Device":
        """Create a device from an API response."""
        return cls(
            device_id=device_id,
            product_id=product_id,
            access_token=access_token,
            name=name,
            online=True,  # We assume it's online if we can get the data
            supports_cooling=supports_cooling
        ) 