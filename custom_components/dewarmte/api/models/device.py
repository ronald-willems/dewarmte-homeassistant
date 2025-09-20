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
    supports_cooling: bool = False
    _info: Optional[DwDeviceInfo] = None


    @property
    def info(self) -> DwDeviceInfo:
        """Return device information."""
        if not self._info:
            # Extract device type from product_id (e.g., "AO A-492" -> "AO")
            device_type = self.product_id.split()[0] if self.product_id else "Unknown"
            
            self._info = DwDeviceInfo(
                name=self.name or f"DeWarmte {self.product_id}",
                model=device_type,  # Set model based on device type
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
            supports_cooling=supports_cooling
        ) 