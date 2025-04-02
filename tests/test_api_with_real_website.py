"""Test the DeWarmte API v1 against a real website."""
import os
import sys
import asyncio
import aiohttp
import yaml
import ssl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api import (
    DeWarmteAuth,
    DeWarmteApiClient,
    ConnectionSettings,
    DeviceOperationSettings,
    HeatCurveSettings,
    WarmWaterRange,
    ThermostatDelay,
    BackupHeatingMode,
    CoolingThermostatType,
    CoolingControlMode,
    HeatCurveMode,
    HeatingKind,
    HeatingPerformanceMode,
    SoundMode,
    PowerLevel,
)

async def main():
    """Test the DeWarmte API v1 with real credentials."""
    print("\n=== Testing DeWarmte API v1 with real credentials ===\n")

    # Load secrets from secrets.yaml
    with open("tests/secrets.yaml", "r") as f:
        secrets = yaml.safe_load(f)

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    session = aiohttp.ClientSession(connector=connector)
    connection_settings = ConnectionSettings(
        username=secrets["dewarmte"]["username"],
        password=secrets["dewarmte"]["password"]
    )
    api = DeWarmteApiClient(
        connection_settings=connection_settings,
        session=session
    )

    print("Testing login...")
    if not await api.async_login():
        print("✗ Login failed")
        await session.close()
        return
    print("✓ Login successful")

    print("\nTesting device info...")
    device = api.device
    if not device:
        print("✗ No device found")
        await session.close()
        return
    print(f"✓ Found device: {device.device_id} (Product ID: {device.product_id})")

    print("\nTesting operation settings...")
    settings = await api.async_get_operation_settings()
    if not settings:
        print("✗ Failed to get operation settings")
        await session.close()
        return
    print("✓ Successfully retrieved operation settings")
    print(f"  - Heating Performance Mode: {settings.heating_performance_mode}")
    print(f"  - Backup Heating Mode: {settings.backup_heating_mode}")
    print(f"  - Heat Curve Mode: {settings.heat_curve.mode}")

    print("\nTesting status data...")
    status_data = await api.async_get_status_data()
    if not status_data:
        print("✗ Failed to get status data")
        await session.close()
        return
    print("✓ Successfully retrieved status data")
    for sensor_key, sensor in status_data.items():
        print(f"  - {sensor.name}: {sensor.value} {sensor.unit}")

    print("\nTesting advanced settings updates...")
    try:
        # Test enabling boost mode with max delay
        await api.async_update_operation_settings({
            "advanced_boost_mode_control": True,
            "advanced_thermostat_delay": "max"
        })
        print("✓ Successfully enabled boost mode with max delay")
        
        # Test disabling boost mode with min delay
        await api.async_update_operation_settings({
            "advanced_boost_mode_control": False,
            "advanced_thermostat_delay": "min"
        })
        print("✓ Successfully disabled boost mode with min delay")
        
        # Test enabling boost mode with medium delay
        await api.async_update_operation_settings({
            "advanced_boost_mode_control": True,
            "advanced_thermostat_delay": "med"
        })
        print("✓ Successfully enabled boost mode with medium delay")
    except Exception as err:
        print(f"Failed to update advanced settings: {err}")
        print("✗ Failed to update advanced settings")

    print("\nAll tests completed!")
    await session.close()

if __name__ == "__main__":
    asyncio.run(main()) 