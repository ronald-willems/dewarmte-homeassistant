"""Test the DeWarmte API v2 against a real website."""
import os
import sys
import asyncio
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.auth import DeWarmteAuth
from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.device import Device

async def main():
    """Test the DeWarmte API v2 with real credentials."""
    print("\n=== Testing DeWarmte API v2 with real credentials ===\n")

    async with aiohttp.ClientSession() as session:
        # Test login
        print("Testing login...")
        auth = DeWarmteAuth("mail@ronaldwillems.nl", "7mb87yba", session)
        success, device_id, product_id, access_token = await auth.login()
        
        if not success:
            print("✗ Login failed")
            return
        
        device = Device.from_api_response(device_id, product_id, access_token)
        print("✓ Login successful")
        print(f"  Device: {device.name or device.device_id}")
        print(f"  Online: {device.is_online}")
        print()

        # Test status data
        print("Testing status data...")
        api = DeWarmteApiClient(device, session, auth)
        try:
            status_data = await api.async_get_status_data()
            if status_data:
                print("✓ Status data retrieved successfully")
                for key, value in status_data.items():
                    print(f"  {key}: {value}")
            else:
                print("✗ Failed to get status data")
        except Exception as err:
            print(f"Failed to get status: {err}")
            print("✗ Failed to get status data")
        print()

        # Test basic settings
        print("Testing basic settings...")
        try:
            settings = await api.async_get_basic_settings()
            if settings:
                print("✓ Basic settings retrieved successfully")
                for key, value in settings.items():
                    print(f"  {key}: {value}")
            else:
                print("✗ Failed to get basic settings")
        except Exception as err:
            print(f"Failed to get settings: {err}")
            print("✗ Failed to get basic settings")

if __name__ == "__main__":
    asyncio.run(main()) 