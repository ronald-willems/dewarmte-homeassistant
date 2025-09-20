"""Test the DeWarmte API v1 against a real website."""
import asyncio
from test_base import TestBase
from custom_components.dewarmte.api.models.status_data import StatusData

async def main():
    """Test the DeWarmte API v1 with real credentials."""
    print("\n=== Testing DeWarmte API v1 with real credentials ===\n")

    try:
        async with TestBase() as test:
            print("Testing device discovery...")
            devices = await test.api.async_discover_devices()
            if not devices:
                print("✗ No devices found")
                return
            
            print(f"✓ Found {len(devices)} device(s):")
            for device in devices:
                print(f"  - {device.device_id} (Product ID: {device.product_id}, Type: {device.product_id.split()[0]})")

            # Test each device
            for device in devices:
                print(f"\n=== Testing device: {device.product_id} ===")
                
                print(f"Testing operation settings for {device.product_id}...")
                settings = await test.api.async_get_operation_settings(device)
                if not settings:
                    print(f"✗ Failed to get operation settings for {device.product_id}")
                    continue
                print(f"✓ Successfully retrieved operation settings for {device.product_id}")
                print(f"  - Heating Performance Mode: {settings.heating_performance_mode}")
                print(f"  - Backup Heating Mode: {settings.backup_heating_mode}")
                print(f"  - Heat Curve Mode: {settings.heat_curve_mode}")
                print(f"  - Sound Mode: {settings.sound_mode}")

                print(f"Testing status data for {device.product_id}...")
                status_data = await test.api.async_get_status_data(device)
                if not status_data:
                    print(f"✗ Failed to get status data for {device.product_id}")
                    continue
                print(f"✓ Successfully retrieved status data for {device.product_id}")
                # Print all non-None values from the StatusData object
                for field in StatusData.__dataclass_fields__:
                    value = getattr(status_data, field)
                    if value is not None:
                        print(f"  - {field}: {value}")

            print("\nAll tests completed!")

    except Exception as err:
        print(f"Error: {err}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())