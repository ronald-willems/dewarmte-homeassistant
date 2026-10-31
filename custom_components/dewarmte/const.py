"""Constants for the DeWarmte integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "dewarmte"

# Configuration constants
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_IMPORT_ENERGY_HISTORY = "import_energy_history"
CONF_DELETE_ENERGY_HISTORY = "delete_energy_history"

# Default values
DEFAULT_UPDATE_INTERVAL = 60  # 1 minute in seconds

# API endpoints
API_BASE_URL = "https://api.mydewarmte.com/v1" 