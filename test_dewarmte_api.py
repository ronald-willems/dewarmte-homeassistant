"""Test the DeWarmte API client."""
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock, AsyncMock

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import ClientSession
from yarl import URL

from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings

@pytest_asyncio.fixture
async def session() -> AsyncGenerator[ClientSession, None]:
    """Create and yield an aiohttp ClientSession."""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest_asyncio.fixture
async def api(session: ClientSession, use_real_website: bool, real_credentials) -> DeWarmteApiClient:
    """Create and yield a DeWarmte API client."""
    print(f"\nCreating API client with use_real_website={use_real_website}")
    username, password = real_credentials if use_real_website else ("test@example.com", "test_password")
    print(f"Using credentials - username: {username}, password: {'*' * len(password) if password else None}")
    
    if use_real_website and (username is None or password is None):
        print("Skipping test - missing credentials")
        pytest.skip("Real website testing requires --username and --password")
    
    settings = ConnectionSettings(
        username=username,
        password=password,
        update_interval=300
    )
    client = DeWarmteApiClient(
        connection_settings=settings,
        session=session
    )
    return client

@pytest.mark.asyncio
async def test_login_success(api: DeWarmteApiClient, use_real_website: bool) -> None:
    """Test successful login."""
    if not use_real_website:
        # Mock the login page response
        login_page_html = """
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="test_csrf_token">
        </form>
        """
        
        # Mock the status page response
        status_page_html = """
        <div>Status page content</div>
        """
        
        with patch.object(api._session, "get") as mock_get, \
             patch.object(api._session, "post") as mock_post:
            # Mock the get request for CSRF token
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.text.return_value = login_page_html
            mock_get.return_value.__aenter__.return_value = mock_get_response

            # Mock the post request for login
            mock_post_response = AsyncMock()
            mock_post_response.status = 200
            mock_post_response.url = URL("https://mydewarmte.com/status/123/A-456/")
            mock_post_response.text.return_value = status_page_html
            mock_post.return_value.__aenter__.return_value = mock_post_response

            assert await api.async_login() is True
    else:
        # Test against real website
        assert await api.async_login() is True

@pytest.mark.asyncio
async def test_get_basic_settings(api: DeWarmteApiClient, use_real_website: bool) -> None:
    """Test getting basic settings."""
    # First login to set up the device
    await test_login_success(api, use_real_website)
    
    if not use_real_website:
        # Mock the settings page response
        settings_html = """
        <form method="post">
            <input type="checkbox" name="default_heating" checked>
            <input type="checkbox" name="force_backup_only">
        </form>
        """
        
        with patch.object(api._session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = settings_html
            mock_get.return_value.__aenter__.return_value = mock_response

            settings = await api.async_get_basic_settings()
            assert settings is not None
            assert isinstance(settings, dict)
            assert len(settings) == 2
            assert settings["default_heating"].state.value is True
            assert settings["force_backup_only"].state.value is False
    else:
        # Test against real website
        settings = await api.async_get_basic_settings()
        assert settings is not None
        assert isinstance(settings, dict)
        assert len(settings) > 0  # At least one setting should be present

@pytest.mark.asyncio
async def test_update_basic_setting(api: DeWarmteApiClient, use_real_website: bool) -> None:
    """Test updating a basic setting."""
    # First login to set up the device
    await test_login_success(api, use_real_website)
    
    if not use_real_website:
        # Mock the settings page responses
        settings_html = """
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="test_csrf_token">
            <input type="checkbox" name="test_setting">
        </form>
        """
        
        with patch.object(api._session, "get") as mock_get, \
             patch.object(api._session, "post") as mock_post:
            # Mock the get request for the settings page
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.text.return_value = settings_html
            mock_get.return_value.__aenter__.return_value = mock_get_response

            # Mock the post request for updating the setting
            mock_post_response = AsyncMock()
            mock_post_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_post_response

            success = await api.async_update_basic_setting("test_setting", True)
            assert success is True
    else:
        # For real website testing, we'll get the current settings first
        settings = await api.async_get_basic_settings()
        if not settings:
            pytest.skip("No settings available to test updating")
        
        # Get the first setting and toggle it
        setting_name = next(iter(settings))
        current_value = settings[setting_name].state.value
        success = await api.async_update_basic_setting(setting_name, not current_value)
        assert success is True
        
        # Toggle it back to original value
        success = await api.async_update_basic_setting(setting_name, current_value)
        assert success is True

@pytest.mark.asyncio
async def test_get_status_data(api: DeWarmteApiClient, use_real_website: bool) -> None:
    """Test getting status data."""
    # First login to set up the device
    await test_login_success(api, use_real_website)
    
    if not use_real_website:
        # Mock the status page response with sensor data
        status_html = """
        <script>
            var SupplyTemp = "45.6";
            var ReturnTemp = "35.2";
            var WaterFlow = "12.5";
            var OutSideTemp = "18.3";
            var HeatInput = "5.2";
            var ElecConsump = "1.8";
            var PompAoOnOff = "1";
            var HeatOutPut = "4.8";
            var BoilerOnOff = "0";
            var ThermostatOnOff = "1";
            var TopTemp = "50.2";
            var BottomTemp = "42.1";
            var HeatOutputPompT = "3.2";
            var ElecConsumpPompT = "0.8";
            var PompTOnOff = "1";
            var PompTHeaterOnOff = "0";
        </script>
        """
        
        with patch.object(api._session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = status_html
            mock_get.return_value.__aenter__.return_value = mock_response

            sensors = await api.async_get_status_data()
            assert sensors is not None
            assert isinstance(sensors, dict)
            assert len(sensors) >= 3
            assert sensors["supply_temp"].state.value == 45.6
            assert sensors["return_temp"].state.value == 35.2
            assert sensors["water_flow"].state.value == 12.5
            assert sensors["outside_temp"].state.value == 18.3
            assert sensors["heat_input"].state.value == 5.2
            assert sensors["elec_consump"].state.value == 1.8
            assert sensors["pump_ao_state"].state.value == 1
            assert sensors["heat_output"].state.value == 4.8
            assert sensors["boiler_state"].state.value == 0
            assert sensors["thermostat_state"].state.value == 1
            assert sensors["top_temp"].state.value == 50.2
            assert sensors["bottom_temp"].state.value == 42.1
            assert sensors["heat_output_pump_t"].state.value == 3.2
            assert sensors["elec_consump_pump_t"].state.value == 0.8
            assert sensors["pump_t_state"].state.value == 1
            assert sensors["pump_t_heater_state"].state.value == 0
    else:
        # Test against real website
        sensors = await api.async_get_status_data()
        assert sensors is not None
        assert isinstance(sensors, dict)
        assert len(sensors) >= 3  # Should have at least a few sensors
        
        # Check that common sensors exist and have reasonable values
        required_sensors = [
            "supply_temp", "return_temp", "water_flow",
            "outside_temp", "heat_input", "elec_consump"
        ]
        for sensor_name in required_sensors:
            assert sensor_name in sensors
            assert sensors[sensor_name].state.value is not None 