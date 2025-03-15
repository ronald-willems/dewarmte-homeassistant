"""Script to examine and update the heating page."""
import asyncio
import yaml
import aiohttp
import json
import ssl
import sys
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime
import websockets
import re
import ast
import html
import argparse

# Add the custom_components directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update DeWarmte heating settings')
    
    # Add mode selection
    parser.add_argument('--mode', choices=['setpoint', 'weather'], default='setpoint',
                       help='Control mode: setpoint (single temperature) or weather (temperature curve)')
    
    # Add temperature settings
    parser.add_argument('--min-supply-temp', type=int, required=True,
                        help='Minimum supply temperature (used at warm outdoor temp in weather mode)')
    parser.add_argument('--max-supply-temp', type=int,
                        help='Maximum supply temperature (used at cold outdoor temp in weather mode)')
    
    # Add outdoor temperature settings for weather mode
    parser.add_argument('--cold-out-temp', type=int, default=-10,
                        help='Cold outdoor temperature where max supply temp is used (default: -10)')
    parser.add_argument('--warm-out-temp', type=int, default=15,
                        help='Warm outdoor temperature where min supply temp is used (default: 15)')
    
    # Add smart correction option
    parser.add_argument('--smart-correction', action='store_true',
                       help='Enable smart correction')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode == 'weather' and args.max_supply_temp is None:
        parser.error('--max-supply-temp is required for weather mode')
    
    if args.mode == 'setpoint' and args.max_supply_temp is not None:
        parser.error('--max-supply-temp should not be used in setpoint mode')
    
    # Validate temperature ranges
    if args.min_supply_temp < 25 or args.min_supply_temp > 60:
        parser.error('Minimum supply temperature must be between 25°C and 60°C')
    
    if args.max_supply_temp is not None and (args.max_supply_temp < 25 or args.max_supply_temp > 60):
        parser.error('Maximum supply temperature must be between 25°C and 60°C')
    
    if args.cold_out_temp >= args.warm_out_temp:
        parser.error('Cold outdoor temperature must be lower than warm outdoor temperature')
    
    if args.mode == 'weather' and args.min_supply_temp >= args.max_supply_temp:
        parser.error('Minimum supply temperature must be lower than maximum supply temperature')
    
    return args

def parse_js_values(script_text):
    """Parse JavaScript values from script text."""
    try:
        # Try to find the current_values variable
        match = re.search(r'var\s+current_values\s*=\s*"([^"]*)"', script_text)
        if match:
            # Get the raw string
            raw_str = match.group(1)
            
            # Unescape the string
            unescaped = raw_str.encode('utf-8').decode('unicode_escape')
            
            # Unescape HTML entities
            unescaped = html.unescape(unescaped)
            
            # Try to parse as Python literal first
            try:
                values = ast.literal_eval(unescaped)
                return values
            except:
                pass
            
            # Try to parse as JSON
            try:
                values = json.loads(unescaped)
                return values
            except:
                pass
            
            # Try to parse manually
            try:
                # Remove curly braces
                content = unescaped.strip('{}')
                
                # Split into key-value pairs
                pairs = content.split(',')
                
                # Parse each pair
                values = {}
                for pair in pairs:
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        key = key.strip().strip("'").strip('"')
                        value = value.strip().strip("'").strip('"')
                        values[key] = value
                
                return values
            except:
                pass
    except Exception as e:
        print(f"Error in parse_js_values: {e}")
    
    return None

async def log_request_response(response, content=None):
    """Log details about a request and response."""
    print(f"\nRequest URL: {response.url}")
    print(f"Request method: {response.method}")
    print(f"Request headers:")
    for k, v in response.request_info.headers.items():
        print(f"  {k}: {v}")
    print(f"\nResponse status: {response.status}")
    print(f"Response headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    if content:
        print("\nResponse content preview:")
        print(content[:500] + "..." if len(content) > 500 else content)

async def countdown(seconds):
    """Display a countdown timer."""
    for i in range(seconds, 0, -1):
        print(f"\rWaiting {i} seconds...", end="", flush=True)
        await asyncio.sleep(1)
    print("\rDone waiting!            ")

async def test_update():
    """Update the heating settings based on command line arguments."""
    print("Starting test...")
    
    # Parse command line arguments
    args = parse_args()
    print(f"\nMode: {args.mode}")
    if args.mode == 'setpoint':
        print(f"Fixed supply temperature: {args.min_supply_temp}°C")
    else:
        print(f"Supply temperature curve:")
        print(f"  {args.max_supply_temp}°C supply at {args.cold_out_temp}°C outdoor")
        print(f"  {args.min_supply_temp}°C supply at {args.warm_out_temp}°C outdoor")
    print(f"Smart correction: {'enabled' if args.smart_correction else 'disabled'}")
    
    try:
        with open("secrets.yaml", "r") as f:
            config = yaml.safe_load(f)["dewarmte"]
        print("Loaded config from secrets.yaml")
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Create SSL context that accepts self-signed certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        # Create connection settings
        settings = ConnectionSettings(
            username=config["username"],
            password=config["password"]
        )
        
        # Create API client
        client = DeWarmteApiClient(settings, session)
        
        # Login
        print("\nAttempting login...")
        if not await client.async_login():
            print("✗ Login failed")
            return
        print("✓ Login successful")
        
        if not client.device:
            print("✗ No device found")
            return
        print(f"✓ Found device: {client.device.device_id} ({client.device.info.model})")
        
        # Get heating page
        print("\nFetching heating page...")
        heating_url = "https://mydewarmte.com/heating/859/A-534/"
        try:
            async with session.get(heating_url, headers=client._auth.headers, ssl=False) as response:
                print(f"Heating page response status: {response.status}")
                if response.status != 200:
                    print(f"✗ Failed to get heating page: {response.status}")
                    return
                
                content = await response.text()
                await log_request_response(response, content)
                
                # Parse the page to get the form details and CSRF token
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find CSRF token
                csrf_token = None
                csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
                if csrf_input:
                    csrf_token = csrf_input.get('value')
                if not csrf_token:
                    print("✗ Failed to find CSRF token")
                    return
                
                # Find form and its action
                form = soup.find('form', {'id': 'setpoint-form'})
                if not form:
                    print("✗ Failed to find form with id 'setpoint-form'")
                    return
                
                # Get form action, default to current URL if not found
                form_action = form.get('action', heating_url)
                if not form_action.startswith('http'):
                    form_action = 'https://mydewarmte.com' + form_action
                
                print(f"\nForm action: {form_action}")
                print(f"CSRF token: {csrf_token}")
                
                # Get current values from JavaScript
                current_values = None
                for script in soup.find_all('script'):
                    if script.string and 'current_values' in script.string:
                        current_values = parse_js_values(script.string)
                        if current_values:
                            print("\nCurrent values:", current_values)
                            break
                
                if not current_values:
                    print("✗ Failed to get current values")
                    return
                
                # First, switch to setpoint control mode
                form_data = {
                    'csrfmiddlewaretoken': csrf_token,
                    'smart_correction_value': str(args.smart_correction).lower()
                }
                
                if args.mode == 'setpoint':
                    # Set both temperatures to the same value for setpoint mode
                    form_data.update({
                        'T_start': str(args.min_supply_temp),
                        'T_end': str(args.min_supply_temp),
                        'T_out_start': str(args.cold_out_temp),
                        'T_out_end': str(args.warm_out_temp),
                        'coord_1_1': str(args.cold_out_temp),
                        'coord_1_2': str(args.warm_out_temp),
                        'coord_2_1': str(args.min_supply_temp),
                        'coord_2_2': str(args.min_supply_temp)
                    })
                else:
                    # Set different temperatures for weather mode
                    # Temperature curve:
                    # - Cold outdoor temp → Maximum supply temp
                    # - Warm outdoor temp → Minimum supply temp
                    form_data.update({
                        'T_start': str(args.max_supply_temp),  # Supply temp at cold outdoor temp
                        'T_end': str(args.min_supply_temp),    # Supply temp at warm outdoor temp
                        'T_out_start': str(args.cold_out_temp),
                        'T_out_end': str(args.warm_out_temp),
                        'coord_1_1': str(args.cold_out_temp),
                        'coord_1_2': str(args.warm_out_temp),
                        'coord_2_1': str(args.max_supply_temp),  # Supply temp at cold outdoor temp
                        'coord_2_2': str(args.min_supply_temp)   # Supply temp at warm outdoor temp
                    })
                
                # Try WebSocket connection first
                ws_url = f"wss://mydewarmte.com/mydewarmte/heating/{client.device.device_id}/"
                try:
                    print("\nAttempting WebSocket connection...")
                    # Get cookies from headers
                    cookies = {}
                    if 'Cookie' in client._auth.headers:
                        for cookie in client._auth.headers['Cookie'].split(';'):
                            if '=' in cookie:
                                name, value = cookie.strip().split('=', 1)
                                cookies[name] = value
                    
                    # Create WebSocket connection
                    async with websockets.connect(
                        ws_url,
                        ssl=ssl_context,
                        extra_headers={
                            'Cookie': f"csrftoken={cookies.get('csrftoken', '')}; sessionid={cookies.get('sessionid', '')}",
                            'X-CSRFToken': client._auth.headers.get('X-CSRFToken', ''),
                            'Origin': 'https://mydewarmte.com',
                            'User-Agent': BROWSER_HEADERS['User-Agent'],
                            'Host': 'mydewarmte.com'
                        }
                    ) as websocket:
                        # Add device ID to form data for WebSocket
                        ws_data = {**form_data, 'id': client.device.device_id}
                        
                        # Send via WebSocket
                        print("\nSending update via WebSocket...")
                        print("WebSocket data:", ws_data)
                        await websocket.send(json.dumps(ws_data))
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            print("WebSocket response:", response)
                        except asyncio.TimeoutError:
                            print("No WebSocket response received")
                            raise
                
                except Exception as ws_error:
                    print(f"WebSocket error: {ws_error}")
                    print("Falling back to HTTP form submission...")
                    
                    # Prepare headers for form submission
                    headers = {
                        **client._auth.headers,
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': 'https://mydewarmte.com',
                        'Referer': heating_url,
                    }
                    
                    # Submit form via HTTP
                    async with session.post(form_action, data=form_data, headers=headers, ssl=False) as response:
                        print(f"\nForm submission response status: {response.status}")
                        content = await response.text()
                        await log_request_response(response, content)
                
                # Force a page reload to ensure changes are persisted
                print("\nForcing page reload to persist changes...")
                headers = {
                    **client._auth.headers,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                async with session.get(heating_url, headers=headers, ssl=False) as response:
                    if response.status != 200:
                        print(f"✗ Failed to reload page: {response.status}")
                    else:
                        print("✓ Page reloaded successfully")
                
                # Wait for the cooldown period
                print("\nWaiting for cooldown period...")
                await countdown(20)
                
                # Verify the change
                print("\nVerifying change...")
                # Add cache-busting query parameter and headers
                verify_url = f"{heating_url}?_={int(time.time())}"
                headers = {
                    **client._auth.headers,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                async with session.get(verify_url, headers=headers, ssl=False) as response:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Check current values in JavaScript
                    new_values = None
                    for script in soup.find_all('script'):
                        if script.string and 'current_values' in script.string:
                            new_values = parse_js_values(script.string)
                            if new_values:
                                print("\nNew values:", new_values)
                                break
                    
                    if new_values:
                        start_temp = new_values.get('startpoint_supplytemperature', '').strip("'")
                        end_temp = new_values.get('endpoint_supplytemperature', '').strip("'")
                        start_out_temp = new_values.get('startpoint_outdoortemperature', '').strip("'")
                        end_out_temp = new_values.get('endpoint_outdoortemperature', '').strip("'")
                        
                        if args.mode == 'setpoint':
                            if start_temp == str(args.min_supply_temp) and end_temp == str(args.min_supply_temp):
                                print("✓ Temperature update successful!")
                            else:
                                print("✗ Temperature update failed - values not changed")
                                print(f"Got: start={start_temp}°C, end={end_temp}°C")
                        else:
                            # Check if values match in either order
                            temps_ok = ((start_temp == str(args.min_supply_temp) and end_temp == str(args.max_supply_temp)) or
                                      (start_temp == str(args.max_supply_temp) and end_temp == str(args.min_supply_temp)))
                            out_temps_ok = ((start_out_temp == str(args.warm_out_temp) and end_out_temp == str(args.cold_out_temp)) or
                                          (start_out_temp == str(args.cold_out_temp) and end_out_temp == str(args.warm_out_temp)))
                            
                            if temps_ok and out_temps_ok:
                                print("✓ Temperature update successful!")
                                print("Current settings:")
                                if start_out_temp == str(args.cold_out_temp):
                                    print(f"  {start_temp}°C supply at {start_out_temp}°C outdoor")
                                    print(f"  {end_temp}°C supply at {end_out_temp}°C outdoor")
                                else:
                                    print(f"  {end_temp}°C supply at {end_out_temp}°C outdoor")
                                    print(f"  {start_temp}°C supply at {start_out_temp}°C outdoor")
                            else:
                                print("✗ Temperature update failed - values not changed")
                                print("Expected:")
                                print(f"  {args.max_supply_temp}°C supply at {args.cold_out_temp}°C outdoor")
                                print(f"  {args.min_supply_temp}°C supply at {args.warm_out_temp}°C outdoor")
                                print("Got:")
                                if start_out_temp == str(args.cold_out_temp):
                                    print(f"  {start_temp}°C supply at {start_out_temp}°C outdoor")
                                    print(f"  {end_temp}°C supply at {end_out_temp}°C outdoor")
                                else:
                                    print(f"  {end_temp}°C supply at {end_out_temp}°C outdoor")
                                    print(f"  {start_temp}°C supply at {start_out_temp}°C outdoor")
                    else:
                        print("✗ Could not verify temperature update - values not found")
                
        except Exception as e:
            print(f"Error during test: {e}")
            return

if __name__ == "__main__":
    print("Starting script...")
    asyncio.run(test_update()) 