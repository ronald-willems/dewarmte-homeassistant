"""Test script for DeWarmte API."""
import asyncio
import json
import os
import sys
from typing import Any

import aiohttp

# Add parent directory to path so we can import the custom component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api import DeWarmteApiClient

def print_section(title: str, data: dict[str, Any]) -> None:
    """Print a section of data with a title."""
    print(f"\n=== {title} ===")
    for key, value in data.items():
        if isinstance(value, dict):
            val = value.get("value")
            unit = value.get("unit", "")
            print(f"{key}: {val} {unit}".strip())
        else:
            print(f"{key}: {value}")

async def get_config() -> dict:
    """Get test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        return None
        
    with open(config_path) as f:
        return json.load(f)

async def test_status_data(api: DeWarmteApiClient) -> None:
    """Test getting status data."""
    print("\nGetting status data...")
    status_data = await api.async_get_status_data()
    if not status_data:
        print("Failed to get status data")
        return

    # Organize and print status data
    temperatures = {k: v for k, v in status_data.items() if "temp" in k.lower()}
    performance = {k: v for k, v in status_data.items() if any(x in k.lower() for x in ["flow", "input", "output", "consump"])}
    states = {k: v for k, v in status_data.items() if "state" in k.lower()}

    print_section("Temperatures", temperatures)
    print_section("Performance Metrics", performance)
    print_section("System States", states)

async def test_basic_settings(api: DeWarmteApiClient) -> None:
    """Test basic settings functionality."""
    print("\nTesting basic settings...")
    
    # Get current settings
    settings = await api.async_get_basic_settings()
    if not settings:
        print("Failed to get basic settings")
        return
    
    print_section("Current Basic Settings", settings)
    
    # Test updating each setting
    for setting_name in settings:
        current_value = settings[setting_name]["value"]
        print(f"\nTesting {setting_name}...")
        
        # Try to toggle the setting
        new_value = not current_value
        print(f"Changing {setting_name} from {current_value} to {new_value}")
        
        success = await api.async_update_basic_setting(setting_name, new_value)
        if success:
            print(f"Successfully updated {setting_name}")
            
            # Verify the change
            updated_settings = await api.async_get_basic_settings()
            if updated_settings and updated_settings[setting_name]["value"] == new_value:
                print("Verified change was successful")
            else:
                print("Warning: Setting may not have been updated correctly")
            
            # Change it back
            print(f"Reverting {setting_name} back to {current_value}")
            success = await api.async_update_basic_setting(setting_name, current_value)
            if success:
                print(f"Successfully reverted {setting_name}")
            else:
                print(f"Failed to revert {setting_name}")
        else:
            print(f"Failed to update {setting_name}")

async def main() -> None:
    """Run the test script."""
    config = await get_config()
    if not config:
        return

    session = aiohttp.ClientSession()
    try:
        api = DeWarmteApiClient(
            username=config["username"],
            password=config["password"],
            session=session
        )

        print("Logging in...")
        if not await api.async_login():
            print("Login failed")
            return
        print("Login successful\n")

        await test_status_data(api)
        await test_basic_settings(api)

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main()) 