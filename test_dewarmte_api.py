"""Test script for DeWarmte API."""
import asyncio
import json
import os
import sys
from typing import Any, Tuple

import aiohttp

from custom_components.dewarmte.api import DeWarmteApiClient

async def get_config() -> dict[str, Any]:
    """Get configuration from config file."""
    config_file = "test_config.json"
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        print("Please create it from test_config.template.json")
        sys.exit(1)
    
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)

async def get_credentials() -> Tuple[str, str]:
    """Get credentials from config file or command line."""
    config = await get_config()
    username = config.get("username")
    password = config.get("password")
    
    if username and password:
        return username, password
    
    # Fall back to command line arguments
    if len(sys.argv) != 3:
        print("Usage: python test_dewarmte_api.py <username> <password>")
        print("Or create a test_config.json file with username and password")
        sys.exit(1)
    
    return sys.argv[1], sys.argv[2]

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
    username, password = await get_credentials()
    
    async with aiohttp.ClientSession() as session:
        api = DeWarmteApiClient(username, password, session)
        
        # Login
        print("Logging in...")
        if not await api.async_login():
            print("Login failed")
            return
        print("Login successful")
        
        # Get status data
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
        
        # Test basic settings
        await test_basic_settings(api)

if __name__ == "__main__":
    asyncio.run(main()) 