#!/usr/bin/env python3
"""Script to test the update functionality of api.py."""
import argparse
import asyncio
import sys
import os
import yaml
import aiohttp
import ssl
from typing import Any

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings

async def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(description="Test the update functionality of api.py")
    parser.add_argument("entity_id", help="The entity ID to update (e.g., select.dewarmte_heating_performance_mode)")
    parser.add_argument("new_state", help="The new state to set")
    args = parser.parse_args()

    # Load secrets from secrets.yaml in tests folder
    secrets_path = os.path.join(os.path.dirname(__file__), "secrets.yaml")
    if not os.path.exists(secrets_path):
        print("secrets.yaml not found in tests directory")
        sys.exit(1)

    with open(secrets_path) as f:
        secrets = yaml.safe_load(f)

    # Extract credentials from dewarmte section
    dewarmte_config = secrets.get("dewarmte", {})
    username = dewarmte_config.get("username")
    password = dewarmte_config.get("password")
    if not username or not password:
        print("dewarmte.username and dewarmte.password must be set in secrets.yaml")
        sys.exit(1)

    # Parse entity ID to get the setting name
    # Example: select.dewarmte_heating_performance_mode -> heating_performance_mode
    if not args.entity_id.startswith(("select.dewarmte_", "number.dewarmte_", "switch.dewarmte_")):
        print("Invalid entity ID format. Must start with select.dewarmte_, number.dewarmte_, or switch.dewarmte_")
        sys.exit(1)

    setting_name = args.entity_id.split("_", 1)[1]

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Initialize API client with SSL context
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        settings = ConnectionSettings(username=username, password=password)
        api = DeWarmteApiClient(settings, session)

        # Login
        if not await api.async_login():
            print("Failed to login")
            sys.exit(1)

        # Get current settings
        if not await api.async_get_operation_settings():
            print("Failed to get current settings")
            sys.exit(1)

        # Convert value based on entity type
        if args.entity_id.startswith("number."):
            try:
                value = float(args.new_state)
            except ValueError:
                print("Value must be a number for number entities")
                sys.exit(1)
        elif args.entity_id.startswith("switch."):
            if args.new_state.lower() not in ["on", "off"]:
                print("Value must be 'on' or 'off' for switch entities")
                sys.exit(1)
            value = args.new_state.lower() == "on"
        else:  # select
            value = args.new_state

        # Update the setting
        try:
            settings = {setting_name: value}
            await api.async_update_operation_settings(settings)
            print(f"Successfully updated {setting_name} to {value}")
        except Exception as err:
            print(f"Failed to update setting: {err}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

