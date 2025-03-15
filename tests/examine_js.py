"""Script to examine JavaScript on the heating page."""
import asyncio
import yaml
from aiohttp import ClientSession, TCPConnector, ClientTimeout
from bs4 import BeautifulSoup
import re
import json
import ssl
import sys
import os
import html
import ast

# Add the custom_components directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings

def python_to_json(python_str):
    """Convert Python literal string to JSON string."""
    try:
        # Parse Python literal string to Python object
        python_obj = ast.literal_eval(python_str)
        # Convert Python object to JSON string
        return json.dumps(python_obj)
    except Exception as e:
        print(f"Error converting Python to JSON: {e}")
        return None

async def main():
    """Log in and examine the heating page JavaScript."""
    print("Starting JavaScript analysis...")
    
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
    
    timeout = ClientTimeout(total=30)
    async with ClientSession(
        connector=TCPConnector(ssl=ssl_context),
        timeout=timeout
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
        
        # Get heating page directly
        print("\nFetching heating page...")
        heating_url = "https://mydewarmte.com/heating/859/A-534/"
        try:
            async with session.get(heating_url, headers=client._auth.headers, ssl=False) as response:
                print(f"Heating page response status: {response.status}")
                if response.status != 200:
                    print(f"✗ Failed to get heating page: {response.status}")
                    return
                
                content = await response.text()
                print("\nParsing page content...")
                
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for current values in JavaScript
                print("\nLooking for current values...")
                for script in soup.find_all('script'):
                    if script.string and 'current_values' in script.string:
                        # Extract the current_values JSON
                        match = re.search(r'var\s+current_values\s*=\s*"([^"]*)"', script.string)
                        if match:
                            # Unescape HTML entities and JSON string
                            python_str = html.unescape(match.group(1))
                            python_str = python_str.encode('utf-8').decode('unicode_escape')
                            # Convert Python literal to JSON
                            json_str = python_to_json(python_str)
                            if json_str:
                                try:
                                    values = json.loads(json_str)
                                    print("\nCurrent values:")
                                    for key, value in values.items():
                                        print(f"  {key}: {value}")
                                except json.JSONDecodeError as e:
                                    print(f"Error parsing JSON: {e}")
                                    print("Raw JSON string:")
                                    print(json_str)
                
                # Look for form details
                print("\nLooking for forms...")
                for form in soup.find_all('form'):
                    print(f"\nForm found:")
                    print(f"Action: {form.get('action')}")
                    print(f"Method: {form.get('method')}")
                    print("Fields:")
                    for field in form.find_all(['input', 'select']):
                        print(f"  {field.get('name')}: type={field.get('type')} id={field.get('id')} value={field.get('value')}")
                    
                    # Look for any form-related JavaScript
                    print("\nForm-related JavaScript:")
                    for script in soup.find_all('script'):
                        if script.string and ('submit' in script.string or 'form' in script.string):
                            print("\nScript with form handling:")
                            print(script.string.strip())
                
                # Look for any AJAX-related JavaScript
                print("\nLooking for AJAX-related JavaScript...")
                for script in soup.find_all('script'):
                    if script.string and ('ajax' in script.string.lower() or 'xhr' in script.string.lower() or 'fetch' in script.string.lower()):
                        print("\nScript with AJAX handling:")
                        print(script.string.strip())
                
                # Look for any event handlers
                print("\nLooking for event handlers...")
                for script in soup.find_all('script'):
                    if script.string and ('addEventListener' in script.string or 'onclick' in script.string or 'onsubmit' in script.string):
                        print("\nScript with event handlers:")
                        print(script.string.strip())
                
                # Look for external JavaScript files
                print("\nLooking for external JavaScript files...")
                external_scripts = []
                for script in soup.find_all('script', src=True):
                    src = script['src']
                    if not src.startswith('http'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = client._auth.base_url + src
                        else:
                            src = client._auth.base_url + '/' + src
                    external_scripts.append(src)
                
                print(f"\nFound {len(external_scripts)} external scripts:")
                for i, src in enumerate(external_scripts):
                    print(f"\nScript {i+1}: {src}")
                    if src.startswith(client._auth.base_url):
                        try:
                            async with session.get(src, headers=client._auth.headers, ssl=False) as response:
                                if response.status == 200:
                                    js_content = await response.text()
                                    print("\nScript content:")
                                    print(js_content)
                                else:
                                    print(f"Failed to fetch script: {response.status}")
                        except Exception as e:
                            print(f"Error fetching script: {e}")
                
        except Exception as e:
            print(f"Error analyzing heating page: {e}")
            return

if __name__ == "__main__":
    print("Starting script...")
    asyncio.run(main()) 