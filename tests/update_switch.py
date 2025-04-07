#!/usr/bin/env python3
"""Script to test the update functionality of api.py."""
"""With this script, you can update the state of a switch or select entity."""
import argparse
import asyncio
import sys
import os
from typing import Any

# Add the custom_components directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.select import MODE_SELECTS
from custom_components.dewarmte.switch import SWITCH_DESCRIPTIONS
from test_base import TestBase

# Mapping of entity settings to API settings
# This is needed because some entity IDs in Home Assistant don't match the API parameter names
# For example, we use 'boost_mode' in Home Assistant but 'advanced_boost_mode_control' in the API
# Note: Select entities don't need mapping as their IDs match the API parameter names exactly
SETTINGS_MAPPING = {
    "boost_mode": "advanced_boost_mode_control",
}

async def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(description="Test the update functionality of api.py")
    parser.add_argument("entity_id", help="The entity ID to update (e.g., select.dewarmte_sound_mode)")
    parser.add_argument("new_state", help="The new state to set (on/off for switches, option for selects)")
    args = parser.parse_args()

    # Parse entity ID to get the setting name
    if not args.entity_id.startswith(("select.dewarmte_", "switch.dewarmte_")):
        print("Invalid entity ID format. Must start with select.dewarmte_ or switch.dewarmte_")
        sys.exit(1)

    entity_type = args.entity_id.split(".")[0]
    setting_name = args.entity_id.split("_", 1)[1]
    
    # Map setting name to API setting name if needed
    api_setting_name = SETTINGS_MAPPING.get(setting_name, setting_name)

    try:
        async with TestBase() as test:
            # Get current settings
            current_settings = await test.api.async_get_operation_settings()
            if not current_settings:
                print("Failed to get current settings")
                sys.exit(1)

            # Convert value based on entity type
            if entity_type == "switch":
                if setting_name not in SWITCH_DESCRIPTIONS:
                    print(f"Invalid switch entity: {setting_name}")
                    print(f"Available switch entities: {', '.join(SWITCH_DESCRIPTIONS.keys())}")
                    sys.exit(1)

                if args.new_state.lower() not in ["on", "off"]:
                    print("Value must be 'on' or 'off' for switch entities")
                    sys.exit(1)
                value = args.new_state.lower() == "on"
                
                # For boost mode, we need to include the current thermostat delay
                if setting_name == "boost_mode":
                    settings = {
                        api_setting_name: value,
                        "advanced_thermostat_delay": current_settings.advanced_thermostat_delay
                    }
                else:
                    settings = {api_setting_name: value}
            else:  # select
                if setting_name not in MODE_SELECTS:
                    print(f"Invalid select entity: {setting_name}")
                    print(f"Available select entities: {', '.join(MODE_SELECTS.keys())}")
                    sys.exit(1)
                
                valid_options = MODE_SELECTS[setting_name].options
                if args.new_state not in valid_options:
                    print(f"Invalid option for {setting_name}")
                    print(f"Available options: {', '.join(valid_options)}")
                    sys.exit(1)
                
                settings = {api_setting_name: args.new_state}

            # Update the setting
            try:
                await test.api.async_update_operation_settings(settings)
                print(f"Successfully updated {setting_name} to {args.new_state}")
            except Exception as err:
                print(f"Failed to update setting: {err}")
                sys.exit(1)

    except Exception as err:
        print(f"Error: {err}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

