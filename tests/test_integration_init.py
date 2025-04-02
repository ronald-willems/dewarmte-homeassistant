"""Test script to simulate DeWarmte integration initialization."""
import asyncio
import logging
import yaml
from datetime import timedelta
from pathlib import Path
from typing import Dict, Any

import aiohttp
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Set up logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# Mock Home Assistant classes and methods
class MockHomeAssistant:
    """Mock Home Assistant instance."""
    def __init__(self):
        self.data = {}
        self.config_entries = MockConfigEntries()
        self.loop = asyncio.get_event_loop()
        self._session = None

    async def async_create_clientsession(self):
        """Create aiohttp client session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_close(self):
        """Close all connections."""
        if self._session:
            await self._session.close()

class MockConfigEntries:
    """Mock config entries."""
    async def async_forward_entry_setups(self, entry, platforms):
        """Mock platform setup."""
        _LOGGER.info("Setting up platforms: %s", platforms)
        return True

    async def async_unload_platforms(self, entry, platforms):
        """Mock platform unload."""
        return True

class MockConfigEntry:
    """Mock config entry."""
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.entry_id = "test_entry_id"

async def test_integration_init():
    """Test the integration initialization."""
    try:
        # Load secrets
        secrets_path = Path(__file__).parent / "secrets.yaml"
        if not secrets_path.exists():
            _LOGGER.error("secrets.yaml not found. Please create it from secrets.template.yaml")
            return False

        with open(secrets_path, "r") as f:
            secrets = yaml.safe_load(f)

        # Create mock Home Assistant instance
        hass = MockHomeAssistant()
        
        # Create mock config entry with credentials
        entry = MockConfigEntry(
            data={
                "username": secrets["username"],
                "password": secrets["password"],
                "update_interval": 300
            }
        )

        # Import the integration
        from custom_components.dewarmte import (
            async_setup_entry,
            async_unload_entry,
            PLATFORMS,
            DOMAIN
        )

        # Initialize the session
        session = await hass.async_create_clientsession()

        # Test setup
        _LOGGER.info("Testing integration setup...")
        try:
            result = await async_setup_entry(hass, entry)
            if result:
                _LOGGER.info("✅ Integration setup successful")
                
                # Check if coordinator was created
                coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
                if coordinator:
                    _LOGGER.info("✅ Coordinator created successfully")
                    _LOGGER.info("Device info: %s", coordinator.device_info)
                    
                    # Test data update
                    _LOGGER.info("Testing data update...")
                    await coordinator.async_refresh()
                    if coordinator.last_update_success:
                        _LOGGER.info("✅ Data update successful")
                    else:
                        _LOGGER.error("❌ Data update failed")
                else:
                    _LOGGER.error("❌ Coordinator not created")
            else:
                _LOGGER.error("❌ Integration setup failed")
        except Exception as e:
            _LOGGER.error("❌ Integration setup failed with error: %s", str(e))
            return False

        # Test unload
        _LOGGER.info("Testing integration unload...")
        try:
            unload_result = await async_unload_entry(hass, entry)
            if unload_result:
                _LOGGER.info("✅ Integration unload successful")
            else:
                _LOGGER.error("❌ Integration unload failed")
        except Exception as e:
            _LOGGER.error("❌ Integration unload failed with error: %s", str(e))
            return False

        return True

    except Exception as e:
        _LOGGER.error("Test failed with error: %s", str(e))
        return False
    finally:
        # Cleanup
        await hass.async_close()

if __name__ == "__main__":
    asyncio.run(test_integration_init()) 