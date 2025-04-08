"""Test the DeWarmte API v1 against a real website."""
import asyncio
from test_base import TestBase

async def main():
    """Test the DeWarmte API v1 with real credentials."""
    print("\n=== Testing DeWarmte API v1 with real credentials ===\n")

    try:
        async with TestBase() as test:
            print("Testing device info...")
            device = test.api.device
            if not device:
                print("✗ No device found")
                return
            print(f"✓ Found device: {device.device_id} (Product ID: {device.product_id})")

            print("\nTesting operation settings...")
            settings = await test.api.async_get_operation_settings()
            if not settings:
                print("✗ Failed to get operation settings")
                return
            print("✓ Successfully retrieved operation settings")
            print(f"  - Heating Performance Mode: {settings.heating_performance_mode}")
            print(f"  - Backup Heating Mode: {settings.backup_heating_mode}")
            print(f"  - Heat Curve Mode: {settings.heat_curve.mode}")

            print("\nTesting status data...")
            status_data = await test.api.async_get_status_data()
            if not status_data:
                print("✗ Failed to get status data")
                return
            print("✓ Successfully retrieved status data")
            for sensor_key, sensor in status_data.items():
                print(f"  - {sensor.name}: {sensor.value} {sensor.unit}")

            print("\nAll tests completed!")

    except Exception as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    asyncio.run(main()) 