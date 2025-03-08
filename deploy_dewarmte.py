"""Deploy script for DeWarmte custom component."""
import asyncio
import json
import os
import sys
import shutil
from typing import Any
from pathlib import Path
import subprocess

async def get_config() -> dict[str, Any]:
    """Get configuration from config file."""
    config_file = "test_config.json"
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        print("Please create it from test_config.template.json")
        sys.exit(1)
    
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)

def is_mounted(mount_point: str) -> bool:
    """Check if a path is mounted."""
    try:
        # Run mount command to check current mounts
        result = subprocess.run(["mount"], capture_output=True, text=True)
        return mount_point in result.stdout
    except:
        return False

async def deploy_to_homeassistant() -> None:
    """Deploy the custom component to Home Assistant."""
    print("\nDeploying to Home Assistant...")
    
    config = await get_config()
    ha_config = config.get("homeassistant")
    if not ha_config:
        print("Home Assistant configuration not found in test_config.json")
        return
    
    # Mount the SMB share
    username = ha_config["username"]
    password = ha_config["password"]
    host = ha_config["host"]
    mount_point = "/Volumes/config"  # Use the standard Volumes directory
    
    # Check if already mounted
    if is_mounted(mount_point):
        print(f"Share already mounted at {mount_point}")
    else:
        print(f"Share not mounted, attempting to mount...")
        
        # Mount using the Finder-style URL
        smb_url = f"smb://{username}:{password}@{host}/config"
        mount_cmd = [
            "open",
            smb_url
        ]
        result = subprocess.run(mount_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Mount error: {result.stderr}")
            return
        
        # Wait a moment for the mount to complete
        print("Waiting for mount to complete...")
        await asyncio.sleep(2)
        
        if not os.path.exists(mount_point):
            print(f"Mount point {mount_point} not found after mounting")
            return
            
        print("Successfully mounted Home Assistant share")
    
    try:
        # Copy the custom component
        custom_components_path = Path(mount_point) / "custom_components"
        if not custom_components_path.exists():
            custom_components_path.mkdir(parents=True)
        
        src_path = Path("custom_components/dewarmte")
        dst_path = custom_components_path / "dewarmte"
        
        print(f"Copying {src_path} to {dst_path}...")
        if dst_path.exists():
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path)
        print("Successfully copied custom component")
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        return

async def main() -> None:
    """Deploy the custom component."""
    await deploy_to_homeassistant()

if __name__ == "__main__":
    asyncio.run(main()) 