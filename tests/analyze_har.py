"""Analyze HAR file to understand the browser's behavior."""
import json
from urllib.parse import parse_qs, urlparse
import re

def format_binary_data(text):
    """Format binary data showing exact characters."""
    result = []
    for char in text:
        if char == '\r':
            result.append('\\r')
        elif char == '\n':
            result.append('\\n')
        else:
            result.append(char)
    return ''.join(result)

def analyze_request_details(entry):
    """Analyze a request in extreme detail."""
    request = entry['request']
    response = entry['response']
    
    print("\n=== DETAILED REQUEST ANALYSIS ===")
    print(f"URL: {request['method']} {request['url']}")
    
    # Headers analysis
    print("\nHEADERS (in exact order):")
    for header in request['headers']:
        print(f"  {header['name']}: {header['value']}")
    
    # Cookie analysis
    cookies = [h for h in request['headers'] if h['name'].lower() == 'cookie']
    if cookies:
        print("\nCOOKIES (parsed):")
        for cookie in cookies:
            cookie_parts = cookie['value'].split('; ')
            for part in cookie_parts:
                print(f"  {part}")
    
    # Form data analysis
    if 'postData' in request:
        post_data = request['postData']
        print("\nPOST DATA:")
        print(f"  MIME Type: {post_data.get('mimeType', 'N/A')}")
        
        if 'text' in post_data:
            print("\nEXACT FORM DATA (showing \\r and \\n):")
            print("-" * 80)
            print(format_binary_data(post_data['text']))
            print("-" * 80)
            
            # Analyze boundary
            boundary_match = re.search(r'boundary=([-\w]+)', post_data['mimeType'])
            if boundary_match:
                print(f"\nBoundary: {boundary_match.group(1)}")
            
            # Analyze form fields
            print("\nFORM FIELDS:")
            parts = post_data['text'].split('--')
            for part in parts:
                if 'Content-Disposition' in part:
                    name_match = re.search(r'name="([^"]+)"', part)
                    if name_match:
                        field_name = name_match.group(1)
                        # Get the value (everything after the double newline)
                        value = part.split('\r\n\r\n')[1].strip() if '\r\n\r\n' in part else ''
                        print(f"  {field_name}: '{value}'")
    
    # Response analysis
    print("\nRESPONSE:")
    print(f"  Status: {response['status']} {response['statusText']}")
    if response.get('content', {}).get('text'):
        print("  Content:")
        print(f"    {response['content']['text']}")

def analyze_har():
    """Analyze the HAR file focusing on the heating update request."""
    with open('tests/network.har', 'r') as f:
        har_data = json.load(f)
    
    entries = har_data['log']['entries']
    
    print("Looking for heating page update request...\n")
    
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if 'heating' in url and request['method'] == 'POST':
            analyze_request_details(entry)
            break

if __name__ == "__main__":
    analyze_har() 