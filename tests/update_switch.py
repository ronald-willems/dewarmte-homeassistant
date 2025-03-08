"""Test script to update a specific switch."""
import asyncio
import json
import os
import sys
import argparse
from typing import Any

import aiohttp

# Add parent directory to path so we can import the custom component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api import DeWarmteApiClient

async def get_config() -> dict:
    """Get test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        return None
        
    with open(config_path) as f:
        return json.load(f)

async def update_switch(api: DeWarmteApiClient, switch_name: str, new_state: bool) -> None:
    """Update a switch to the specified state."""
    print(f"\nUpdating {switch_name}...")
    
    # Get current state
    settings = await api.async_get_basic_settings()
    if not settings or switch_name not in settings:
        print(f"Failed to get {switch_name} setting")
        return
    
    current_state = settings[switch_name]["value"]
    print(f"Current {switch_name} state: {current_state}")
    
    if current_state == new_state:
        print(f"{switch_name} is already {'enabled' if new_state else 'disabled'}")
        return
    
    # Set new state
    print(f"Setting {switch_name} to {new_state}")
    success = await api.async_update_basic_setting(switch_name, new_state)
    if success:
        print(f"Successfully set {switch_name} to {new_state}")
        
        # Verify the change
        settings = await api.async_get_basic_settings()
        if settings and settings[switch_name]["value"] == new_state:
            print(f"Verified {switch_name} is now {new_state}")
        else:
            print(f"Warning: {switch_name} may not have been set correctly")
    else:
        print(f"Failed to set {switch_name}")

async def main() -> None:
    """Run the test script."""
    parser = argparse.ArgumentParser(description='Update a DeWarmte switch state.')
    parser.add_argument('switch_name', help='Name of the switch to update')
    parser.add_argument('--state', type=lambda x: x.lower() == 'true', 
                      default=True, help='State to set (true/false)')
    args = parser.parse_args()

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

        await update_switch(api, args.switch_name, args.state)

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main()) 