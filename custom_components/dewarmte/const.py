"""Constants for the DeWarmte integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "dewarmte"

# Configuration constants
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 60  # 1 minute in seconds

# API endpoints
API_BASE_URL = "https://api.mydewarmte.com/v1" 