# DeWarmte API v2

This folder contains the DeWarmte API client implementation and documentation.

## Structure

- `auth.py` - Authentication handling
- `client.py` - Main API client
- `openapi.yaml` - OpenAPI specification
- `models/` - Data models
  - `base.py` - Base model classes
  - `device.py` - Device models
  - `sensor.py` - Sensor models
  - `settings.py` - Settings models

## API Overview

The DeWarmte API is a REST API that uses JWT authentication. The main features are:

1. Authentication
   - Login with email/password
   - JWT token-based authentication

2. Device Management
   - Get device information
   - Get device status
   - Get outdoor temperature

3. Settings Management
   - Get/Update general settings
   - Heat curve settings
   - Heating performance settings
   - Backup heating settings
   - Advanced settings (boost mode and thermostat delay)

## API Documentation

See `openapi.yaml` for the complete API specification. You can view this file in any OpenAPI/Swagger viewer, such as:
- [Swagger Editor](https://editor.swagger.io/)
- [Redocly](https://redocly.github.io/redoc/)
- [Stoplight Studio](https://stoplight.io/studio)

## Usage Example

```python
import aiohttp
from custom_components.dewarmte.api import DeWarmteApiClient, ConnectionSettings

async def main():
    # Create connection settings
    settings = ConnectionSettings(
        username="your_email",
        password="your_password"
    )
    
    # Create API client
    async with aiohttp.ClientSession() as session:
        api = DeWarmteApiClient(settings, session)
        
        # Login
        if await api.async_login():
            # Get device settings
            settings = await api.async_get_operation_settings()
            print(f"Current settings: {settings}")
            
            # Update settings
            await api.async_update_operation_settings({
                "advanced_boost_mode_control": True,
                "advanced_thermostat_delay": "max"
            })
``` 