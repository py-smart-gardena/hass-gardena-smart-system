#!/usr/bin/env python3
"""Test script for Gardena Smart System authentication."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.gardena_smart_system.auth import GardenaAuthError, GardenaAuthenticationManager
from custom_components.gardena_smart_system.gardena_client import GardenaAPIError, GardenaSmartSystemClient


# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_authentication():
    """Complete authentication test."""
    print("🔐 Gardena Smart System Authentication Test")
    print("=" * 50)
    
    # Get credentials from environment variables
    client_id = os.getenv("GARDENA_CLIENT_ID")
    client_secret = os.getenv("GARDENA_CLIENT_SECRET")
    api_key = os.getenv("GARDENA_API_KEY")
    
    if not client_id or not client_secret:
        print("❌ Error: Missing environment variables")
        print("   Set GARDENA_CLIENT_ID and GARDENA_CLIENT_SECRET")
        return False
    
    print(f"✅ Client ID: {client_id[:8]}...")
    print(f"✅ Client Secret: {'*' * len(client_secret)}")
    if api_key:
        print(f"✅ API Key: {api_key[:8]}...")
    else:
        print("ℹ️  API Key: Not defined (optional)")
    
    print("\n🚀 Testing authentication manager...")
    
    try:
        # Test authentication manager
        auth_manager = GardenaAuthenticationManager(client_id, client_secret, api_key)
        
        # Test initial authentication
        print("   📡 Initial authentication...")
        token = await auth_manager.authenticate()
        print(f"   ✅ Token obtained: {token[:20]}...")
        
        # Test token validation
        print("   🔍 Token validation...")
        is_valid = auth_manager._is_token_valid()
        print(f"   ✅ Token valid: {is_valid}")
        
        # Test authentication headers
        print("   📋 Authentication headers...")
        headers = auth_manager.get_auth_headers()
        print(f"   ✅ Headers generated: {list(headers.keys())}")
        
        print("\n🚀 Testing API client...")
        
        # Test API client
        client = GardenaSmartSystemClient(client_id, client_secret, api_key)
        
        # Test location retrieval
        print("   📍 Retrieving locations...")
        locations = await client.get_locations()
        print(f"   ✅ {len(locations)} location(s) found")
        
        if locations:
            location_id = locations[0]["id"]
            location_name = locations[0].get("attributes", {}).get("name", "Unnamed")
            print(f"   📍 Location: {location_name} ({location_id})")
            
            # Test location details retrieval
            print("   🔍 Location details...")
            location_data = await client.get_location(location_id)
            devices = location_data.get("included", [])
            print(f"   ✅ {len(devices)} device(s) found")
            
            # Display device types
            device_types = {}
            for device in devices:
                device_type = device.get("type", "UNKNOWN")
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            print("   📊 Device types:")
            for device_type, count in device_types.items():
                print(f"      - {device_type}: {count}")
        
        # Test WebSocket URL creation
        print("   🔌 WebSocket test...")
        try:
            websocket_data = await client.create_websocket_url(location_id)
            print("   ✅ WebSocket URL created successfully")
        except Exception as e:
            print(f"   ⚠️  WebSocket error: {e}")
        
        # Cleanup
        await client.close()
        await auth_manager.close()
        
        print("\n🎉 All authentication tests passed!")
        return True
        
    except GardenaAuthError as e:
        print(f"\n❌ Authentication error: {e}")
        if e.status_code:
            print(f"   Error code: {e.status_code}")
        if e.response_data:
            print(f"   Response data: {e.response_data}")
        return False
        
    except GardenaAPIError as e:
        print(f"\n❌ API error: {e}")
        if e.status_code:
            print(f"   Error code: {e.status_code}")
        if e.response_data:
            print(f"   Response data: {e.response_data}")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("Detailed error:")
        return False


async def test_error_scenarios():
    """Test error scenarios."""
    print("\n🧪 Testing error scenarios...")
    print("=" * 50)
    
    # Test with invalid credentials
    print("🔍 Test with invalid credentials...")
    try:
        auth_manager = GardenaAuthenticationManager("invalid", "invalid")
        await auth_manager.authenticate()
        print("   ❌ Error: Authentication should have failed")
        return False
    except GardenaAuthError as e:
        print(f"   ✅ Expected authentication error: {e}")
    
    # Test with empty credentials
    print("🔍 Test with empty credentials...")
    try:
        auth_manager = GardenaAuthenticationManager("", "")
        await auth_manager.authenticate()
        print("   ❌ Error: Authentication should have failed")
        return False
    except Exception as e:
        print(f"   ✅ Expected error: {e}")
    
    print("✅ All error tests passed!")
    return True


async def main():
    """Main function."""
    print("🧪 Gardena Smart System Authentication Test Script")
    print("=" * 60)
    
    # Main test
    auth_success = await test_authentication()
    
    # Error scenario tests
    error_success = await test_error_scenarios()
    
    print("\n" + "=" * 60)
    if auth_success and error_success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        logger.exception("Detailed error:")
        sys.exit(1) 