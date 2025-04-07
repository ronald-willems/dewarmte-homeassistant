#!/usr/bin/env python3
"""Script to test the update functionality of api.py."""
"""With this script, you can update the state of a switch or select entity."""
import argparse
import asyncio
import sys
import os

# Add the custom_components directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.select import MODE_SELECTS
from custom_components.dewarmte.switch import SWITCH_DESCRIPTIONS
from test_base import TestBase

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

    try:
        async with TestBase() as test:
            # Validate the entity exists
            if entity_type == "switch" and setting_name not in SWITCH_DESCRIPTIONS:
                print(f"Invalid switch entity: {setting_name}")
                print(f"Available switch entities: {', '.join(SWITCH_DESCRIPTIONS.keys())}")
                sys.exit(1)
            elif entity_type == "select" and setting_name not in MODE_SELECTS:
                print(f"Invalid select entity: {setting_name}")
                print(f"Available select entities: {', '.join(MODE_SELECTS.keys())}")
                sys.exit(1)

            # Validate the value
            if entity_type == "switch":
                if args.new_state.lower() not in ["on", "off"]:
                    print("Value must be 'on' or 'off' for switch entities")
                    sys.exit(1)
                value = args.new_state.lower() == "on"
            else:  # select
                valid_options = MODE_SELECTS[setting_name].options
                if args.new_state not in valid_options:
                    print(f"Invalid option for {setting_name}")
                    print(f"Available options: {', '.join(valid_options)}")
                    sys.exit(1)
                value = args.new_state

            # Update the setting
            try:
                await test.api.async_update_operation_settings({setting_name: value})
                print(f"Successfully updated {setting_name} to {args.new_state}")
            except Exception as err:
                print(f"Failed to update setting: {err}")
                sys.exit(1)

    except Exception as err:
        print(f"Error: {err}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

