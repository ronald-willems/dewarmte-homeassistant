"""Application configuration models for DeWarmte API."""
from dataclasses import dataclass

@dataclass
class ConnectionSettings:
    """Connection settings for DeWarmte API."""
    username: str
    password: str
    update_interval: int 