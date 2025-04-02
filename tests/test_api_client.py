"""Test the simple DeWarmte API client."""
import asyncio
import logging
import os
import sys
from typing import Any

import yaml

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from custom_components.dewarmte.api.simple_client import DeWarmteSimpleApiClient

# Configure logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_status_data(client: DeWarmteSimpleApiClient, device_id: str) -> bool:
    """Test getting status data.

    Args:
        client: The API client
        device_id: The ID of the device

    Returns:
        bool: True if test passed, False otherwise
    """
    try:
        _LOGGER.info("Testing status data retrieval...")
        status_data = await client.get_status_data(device_id)
        if not status_data:
            _LOGGER.error("Failed to get status data")
            return False

        _LOGGER.info("Status data retrieved successfully:")
        _LOGGER.info("  Water Flow: %.1f L/min", status_data.water_flow)
        _LOGGER.info("  Supply Temperature: %.1f °C", status_data.supply_temperature)
        _LOGGER.info("  Outdoor Temperature: %.1f °C", status_data.outdoor_temperature)
        _LOGGER.info("  Heat Input: %.1f kW", status_data.heat_input)
        _LOGGER.info("  Actual Temperature: %.1f °C", status_data.actual_temperature)
        _LOGGER.info("  Electricity Consumption: %.1f kW", status_data.electricity_consumption)
        _LOGGER.info("  Heat Output: %.1f kW", status_data.heat_output)
        _LOGGER.info("  Gas Boiler: %s", status_data.gas_boiler)
        _LOGGER.info("  Thermostat: %s", status_data.thermostat)
        _LOGGER.info("  Target Temperature: %.1f °C", status_data.target_temperature)
        _LOGGER.info("  Electric Backup Usage: %.1f kW", status_data.electric_backup_usage)
        return True
    except Exception as e:
        _LOGGER.error("Error testing status data: %s", str(e))
        return False

async def main() -> None:
    """Run the tests."""
    # Load secrets
    secrets_path = os.path.join(os.path.dirname(__file__), "secrets.yaml")
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            secrets = yaml.safe_load(f)
    except Exception as e:
        _LOGGER.error("Failed to load secrets: %s", str(e))
        return

    # Create API client
    client = DeWarmteSimpleApiClient(
        username=secrets["dewarmte"]["username"],
        password=secrets["dewarmte"]["password"],
        verify_ssl=False,  # Disable SSL verification for testing
    )

    try:
        # Login
        _LOGGER.info("Testing login...")
        if not await client.login():
            _LOGGER.error("Login failed")
            return
        _LOGGER.info("Login successful")

        # Get device info
        _LOGGER.info("Testing device info retrieval...")
        device = await client.get_device_info()
        if not device:
            _LOGGER.error("Failed to get device info")
            return
        _LOGGER.info("Device info retrieved successfully:")
        _LOGGER.info("  Device ID: %s", device.device_id)
        _LOGGER.info("  Product ID: %s", device.product_id)
        _LOGGER.info("  Model: %s", device.info.model)
        _LOGGER.info("  Software Version: %s", device.info.sw_version)
        _LOGGER.info("  Hardware Version: %s", device.info.hw_version)
        _LOGGER.info("  Online: %s", device.is_online)

        # Test status data
        if not await test_status_data(client, device.device_id):
            return

        _LOGGER.info("All tests completed successfully")
    except Exception as e:
        _LOGGER.error("Error during tests: %s", str(e))
    finally:
        await client.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(main()) 