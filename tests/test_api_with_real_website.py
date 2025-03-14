"""Manual test script for DeWarmte API against real website."""
import asyncio
import yaml
from aiohttp import ClientSession
from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings

async def test_real_api():
    """Test the API against the real website."""
    # Load credentials
    with open("secrets.yaml", "r") as f:
        config = yaml.safe_load(f)

    print("\n=== Testing DeWarmte API with real credentials ===")
    
    async with ClientSession() as session:
        # Initialize API
        connection_settings = ConnectionSettings(
            username=config["dewarmte"]["username"],
            password=config["dewarmte"]["password"]
        )
        api = DeWarmteApiClient(connection_settings=connection_settings, session=session)

        # Test login
        print("\nTesting login...")
        if await api.async_login():
            print("✓ Login successful")
        else:
            print("✗ Login failed")
            return

        # Test status data
        print("\nTesting status data...")
        status = await api.async_get_status_data()
        if status:
            print("✓ Status data retrieved:")
            for key, value in status.items():
                print(f"  {key}: {value.state.value} {value.state.unit or ''}")
        else:
            print("✗ Failed to get status data")

        # Test basic settings
        print("\nTesting basic settings...")
        settings = await api.async_get_basic_settings()
        if settings:
            print("✓ Basic settings retrieved:")
            for key, value in settings.items():
                print(f"  {key}: {value.state.value}")
        else:
            print("✗ Failed to get basic settings")

def main():
    """Run the test script."""
    asyncio.run(test_real_api())

if __name__ == "__main__":
    main() 