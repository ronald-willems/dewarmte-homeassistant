"""Settings group model for DeWarmte API."""
from dataclasses import dataclass
from typing import List

@dataclass
class SettingsGroup:
    """Represents a group of related settings that are updated together."""
    endpoint: str
    keys: List[str]

