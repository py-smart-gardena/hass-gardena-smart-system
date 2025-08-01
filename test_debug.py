#!/usr/bin/env python3
"""Debug script to test Gardena data structure."""

import asyncio
import os
import sys

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.gardena_smart_system.auth import GardenaAuthenticationManager
from custom_components.gardena_smart_system.gardena_client import GardenaSmartSystemClient

async def debug_data():
    """Debug the data structure."""
    # Get credentials from environment
    client_id = os.getenv('GARDENA_CLIENT_ID')
    client_secret = os.getenv('GARDENA_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Please set GARDENA_CLIENT_ID and GARDENA_CLIENT_SECRET environment variables")
        return
    
    # Create auth manager and client
    auth_manager = GardenaAuthenticationManager(client_id, client_secret)
    client = GardenaSmartSystemClient(auth_manager)
    
    try:
        # Get locations
        print("Fetching locations...")
        locations = await client.get_locations()
        print(f"Found {len(locations)} locations")
        
        for location in locations:
            print(f"\nLocation: {location.name} ({location.id})")
            print(f"Devices: {len(location.devices)}")
            
            for device_id, device in location.devices.items():
                print(f"\n  Device: {device.name} ({device_id})")
                print(f"    Model: {device.model_type}")
                print(f"    Serial: {device.serial}")
                print(f"    Services: {list(device.services.keys())}")
                
                for service_type, service in device.services.items():
                    print(f"      {service_type}: {service.id}")
                    if hasattr(service, 'activity'):
                        print(f"        Activity: {service.activity}")
                    if hasattr(service, 'state'):
                        print(f"        State: {service.state}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_data()) 