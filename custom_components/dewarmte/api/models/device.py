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

#TODO: Device handling is overly complex. See also client.p
# Device and DWDeviceInfo classes should be merged. 
# sw and hw version are not available in the API response.
# Important: keep entity ID generation backward compatible.
@dataclass
class Device:
    """Device model."""
    device_id: str
    product_id: str
    access_token: str
    device_type: str
    name: str | None = None
    supports_cooling: bool = False
    _info: Optional[DwDeviceInfo] = None

    @property
    def info(self) -> DwDeviceInfo:
        """Return device information."""
        if not self._info:
            self._info = DwDeviceInfo(
                name=self.name or f"DeWarmte {self.product_id}",
                model=self.device_type,  # Set model based on device type
            )
        return self._info

    @classmethod
    def from_api_response(cls, device_id: str, product_id: str, access_token: str, device_type: str, name: Optional[str] = None, supports_cooling: bool = False) -> "Device":
        """Create a device from an API response."""
        return cls(
            device_id=device_id,
            product_id=product_id,
            access_token=access_token,
            device_type=device_type,
            name=name,
            supports_cooling=supports_cooling
        ) 