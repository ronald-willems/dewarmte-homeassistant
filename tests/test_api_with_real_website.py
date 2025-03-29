"""Test the DeWarmte API v2 against a real website."""
import os
import sys
import asyncio
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.auth import DeWarmteAuth
from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.device import Device
from custom_components.dewarmte.models.settings import ConnectionSettings

async def main():
    """Test the DeWarmte API v2 with real credentials."""
    print("\n=== Testing DeWarmte API v2 with real credentials ===\n")

    async with aiohttp.ClientSession() as session:
        # Create connection settings
        settings = ConnectionSettings(
            username="mail@ronaldwillems.nl",
            password="7mb87yba",
            update_interval=60
        )
        
        # Create API client
        api = DeWarmteApiClient(connection_settings=settings, session=session)
        
        # Test login
        print("Testing login...")
        if not await api.async_login():
            print("✗ Login failed")
            return
        
        print("✓ Login successful")
        print(f"  Device: {api.device.name or api.device.device_id}")
        print(f"  Online: {api.device.is_online}")
        print()

        # Test status data
        print("Testing status data...")
        try:
            status_data = await api.async_get_status_data()
            if status_data:
                print("✓ Status data retrieved successfully")
                for key, sensor in status_data.items():
                    print(f"  {sensor.name}: {sensor.value} {sensor.unit or ''}")
            else:
                print("✗ Failed to get status data")
        except Exception as err:
            print(f"Failed to get status: {err}")
            print("✗ Failed to get status data")
        print()

        # Test operation settings
        print("Testing operation settings...")
        try:
            settings = await api.async_get_operation_settings()
            if settings:
                print("✓ Operation settings retrieved successfully")
                print("\nHeat Curve Settings:")
                print(f"  Mode: {settings.heat_curve.mode}")
                print(f"  Heating Kind: {settings.heat_curve.heating_kind}")
                print(f"  S1 Outside Temperature: {settings.heat_curve.s1_outside_temp_celsius}°C")
                print(f"  S1 Target Temperature: {settings.heat_curve.s1_target_temp_celsius}°C")
                print(f"  S2 Outside Temperature: {settings.heat_curve.s2_outside_temp_celsius}°C")
                print(f"  S2 Target Temperature: {settings.heat_curve.s2_target_temp_celsius}°C")
                print(f"  Fixed Temperature: {settings.heat_curve.fixed_temperature_celsius}°C")
                print(f"  Smart Correction: {settings.heat_curve.use_smart_correction}")
                
                print("\nPerformance Settings:")
                print(f"  Mode: {settings.heating_performance_mode}")
                print(f"  Backup Temperature: {settings.heating_performance_backup_temperature}°C")
                
                print("\nSound Settings:")
                print(f"  Mode: {settings.sound_mode}")
                print(f"  Compressor Power: {settings.sound_compressor_power}")
                print(f"  Fan Speed: {settings.sound_fan_speed}")
                
                print("\nWarm Water Settings:")
                print(f"  Scheduled: {settings.warm_water_is_scheduled}")
                for range in settings.warm_water_ranges:
                    print(f"  Range {range.order}: {range.temperature}°C at {range.period}")
            else:
                print("✗ Failed to get operation settings")
        except Exception as err:
            print(f"Failed to get settings: {err}")
            print("✗ Failed to get operation settings")

if __name__ == "__main__":
    asyncio.run(main()) 