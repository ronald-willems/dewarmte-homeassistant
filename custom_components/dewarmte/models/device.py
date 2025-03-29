"""Device model for DeWarmte."""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Device:
    """Device model."""
    device_id: str
    product_id: str
    access_token: str
    name: Optional[str] = None
    online: bool = False

    @property
    def is_online(self) -> bool:
        """Return if the device is online."""
        return self.online

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