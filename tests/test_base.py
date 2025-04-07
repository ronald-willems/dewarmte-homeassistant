"""Base test script for DeWarmte API tests."""
import os
import sys
import asyncio
import aiohttp
import yaml
import ssl
import logging
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api import (
    DeWarmteAuth,
    DeWarmteApiClient,
    ConnectionSettings,
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

class TestBase:
    """Base class for DeWarmte API tests."""
    
    def __init__(self):
        """Initialize the test base."""
        self._session = None
        self.api = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    def _load_secrets(self) -> dict:
        """Load secrets from secrets.yaml."""
        secrets_path = os.path.join(os.path.dirname(__file__), "secrets.yaml")
        if not os.path.exists(secrets_path):
            raise FileNotFoundError("secrets.yaml not found")
        
        with open(secrets_path, "r") as f:
            secrets = yaml.safe_load(f)
        
        if not secrets.get("dewarmte", {}).get("username") or not secrets.get("dewarmte", {}).get("password"):
            raise ValueError("Username and password must be provided in secrets.yaml")
        
        return secrets["dewarmte"]

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context that doesn't verify certificates."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def setup(self) -> None:
        """Set up the test environment."""
        try:
            # Load secrets
            secrets = self._load_secrets()
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
            # Create session
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(connector=connector)
            
            # Create API client
            connection_settings = ConnectionSettings(
                username=secrets["username"],
                password=secrets["password"]
            )
            self.api = DeWarmteApiClient(
                connection_settings=connection_settings,
                session=self._session
            )
            
            # Login
            if not await self.api.async_login():
                raise ValueError("Login failed")
                
        except Exception as err:
            await self.cleanup()
            raise err

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None 