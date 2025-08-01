# Gardena Smart System Integration for Home Assistant - Development Rules

## 🎯 Project Overview
This is a Home Assistant custom integration for Gardena Smart System devices. The integration provides real-time control and monitoring of Gardena devices (lawn mowers, valves, sensors, power sockets) through the Gardena Smart System API v2.

## 🏗️ Architecture

### Core Components
- **Authentication**: OAuth2 with Husqvarna/Gardena API
- **API Client**: REST API client for initial data loading
- **WebSocket Client**: Real-time event handling
- **Coordinator**: Data management and entity updates
- **Entity Platforms**: Home Assistant entities for each device type

### Key Files
- `custom_components/gardena_smart_system/__init__.py` - Main entry point
- `custom_components/gardena_smart_system/coordinator.py` - Data coordinator
- `custom_components/gardena_smart_system/gardena_client.py` - API client
- `custom_components/gardena_smart_system/websocket_client.py` - WebSocket client
- `custom_components/gardena_smart_system/auth.py` - Authentication manager
- `custom_components/gardena_smart_system/models.py` - Data models and parser

## 🔧 Development Environment

### Setup Commands
```bash
make setup          # Setup complete development environment
make ha-start       # Start Home Assistant with integration
make ha-stop        # Stop Home Assistant
make ha-logs        # View Home Assistant logs
make ha-reset       # Reset Home Assistant environment
make test           # Run all tests
make test-auth      # Run authentication tests only
```

### Environment Variables
- `GARDENA_CLIENT_ID` - Your Gardena Client ID
- `GARDENA_CLIENT_SECRET` - Your Gardena Client Secret
- `GARDENA_API_KEY` - Your Gardena API Key treived from authentification

## 📡 API Optimization Strategy

### Current Implementation (Optimized)
The integration now uses a **minimal API approach** to avoid rate limiting (429 errors):

1. **Authentication** (1 call at startup)
   - OAuth2 token request to Husqvarna authentication server
   - Automatic token refresh when needed

2. **Initial Data Loading** (1 call at startup)
   - Single call to `/locations` to get all locations and devices
   - Data stored in memory, no periodic reloading

3. **WebSocket Connection** (persistent)
   - Real-time updates via WebSocket
   - Automatic reconnection on disconnection
   - All device state changes come through WebSocket

### API Calls Reduction
- **Before**: ~1442 calls per day (polling every 60s)
- **After**: 2 calls per day (startup only)
- **Reduction**: 99.86% fewer API calls

## 🏠 Home Assistant Integration

### Supported Platforms
- `lawn_mower` - Gardena lawn mowers (SILENO, etc.)
- `valve` - Irrigation control valves
- `switch` - Power sockets
- `sensor` - Environmental sensors (temperature, humidity, light)
- `binary_sensor` - Battery status sensors

### Entity Structure
Each device can have multiple services:
- `COMMON` - Device information, battery, RF link status
- `MOWER` - Mower-specific data (activity, operating hours)
- `VALVE` - Valve control and status
- `POWER_SOCKET` - Power socket control
- `SENSOR` - Sensor readings

### Data Models
- `GardenaLocation` - Location with devices
- `GardenaDevice` - Device with multiple services
- `GardenaService` - Service-specific data (Mower, Valve, etc.)

## 🔐 Authentication

### OAuth2 Flow Implementation
The integration uses **Client Credentials Grant** OAuth2 flow with the Husqvarna/Gardena authentication system:

1. **Initial Authentication**:
   - `POST /v1/oauth2/token` with `grant_type=client_credentials`
   - Requires `client_id` and `client_secret`
   - Returns `access_token` and `expires_in`

2. **Token Management**:
   - Automatic token validation before each request
   - Token refresh 5 minutes before expiration
   - Thread-safe authentication with async locks

3. **SSL Context Handling**:
   - Cached SSL context for performance
   - Development mode bypass for macOS SSL issues
   - Proper SSL context management in async environment

### Authentication Headers
All API requests require these headers:
```python
{
    "Authorization": "Bearer <access_token>",
    "Authorization-Provider": "husqvarna",
    "X-Api-Key": "<client_id>",
    "Content-Type": "application/vnd.api+json"
}

```

### Error Handling
- **401 Unauthorized**: Token expired or invalid
- **403 Forbidden**: Insufficient permissions
- **429 Too Many Requests**: Rate limiting (handled by optimization)
- **Network Errors**: Automatic retry with exponential backoff

### Security Best Practices
- Tokens stored in memory only (not persisted)
- Automatic token invalidation on refresh failure
- Secure token expiration handling
- No sensitive data in logs
- SSL context caching for performance
- Proper async/await patterns for authentication
- Thread-safe token management with locks

### Authentication Implementation Details
Based on the SmartSystem library patterns:

1. **SSL Context Management**:
   ```python
   @functools.lru_cache(maxsize=1)
   def get_ssl_context():
       context = ssl.create_default_context()
       return context
   ```

2. **Token Refresh Strategy**:
   - Check token validity before each request
   - Refresh 5 minutes before expiration
   - Use refresh token when available
   - Fallback to client credentials if refresh fails

3. **Error Recovery**:
   - Automatic retry with exponential backoff
   - Graceful degradation on authentication failures
   - Proper cleanup on token revocation

## 🌐 WebSocket Implementation

### Connection Process
1. Get WebSocket URL from `/websocket` endpoint
2. Connect with authentication headers
3. Listen for real-time service updates
4. Automatic reconnection with exponential backoff

### Message Types
- Service updates: Direct service data (VALVE, MOWER, etc.)
- Ping/Pong: Keep-alive messages
- Error handling: Connection failures and reconnection

## 🧪 Testing

### Test Structure
- `test_auth.py` - Authentication and API client tests
- `test_models.py` - Data model and parser tests
- `test_entities.py` - Entity base class tests
- `test_websocket.py` - WebSocket client tests
- `test_websocket_integration.py` - Integration tests

### Test Commands
```bash
make test           # Run all tests
make test-auth      # Authentication tests only
make test-real      # Real-world authentication test
```

## 🐛 Common Issues & Solutions

### SSL Certificate Issues (macOS)
- Enable `dev_mode=True` in client initialization
- Automatically bypasses SSL verification in development

### Rate Limiting (429 Errors)
- Caused by too many API calls
- **Solution**: Use WebSocket for real-time updates instead of polling
- Current implementation: Only 2 API calls per day

### Entity Not Appearing
- Check if device has required services (COMMON, MOWER, etc.)
- Verify unique IDs are correctly generated
- Check Home Assistant logs for entity registration errors

### WebSocket Connection Issues
- Verify authentication is working
- Check if locationId is correctly retrieved
- Ensure WebSocket URL is valid

## 📝 Code Standards

### Python Conventions
- Use type hints throughout
- Follow Home Assistant entity patterns
- Use async/await for all I/O operations
- Comprehensive error handling and logging

### Authentication Patterns
Based on SmartSystem library best practices:

1. **SSL Context Caching**:
   ```python
   @functools.lru_cache(maxsize=1)
   def get_ssl_context():
       return ssl.create_default_context()
   ```

2. **Exponential Backoff**:
   ```python
   @backoff.on_exception(backoff.expo, HTTPStatusError, max_value=900)
   async def api_call():
       # API call with automatic retry
   ```

3. **Token Management**:
   ```python
   async def authenticate(self):
       async with self._auth_lock:
           if self._is_token_valid():
               return self._access_token
           # Perform authentication
   ```

4. **Error Handling**:
   ```python
   try:
       response = await client.get(url)
       response.raise_for_status()
   except HTTPStatusError as e:
       if e.response.status_code == 401:
           raise AuthenticationException("Token expired")
   ```

### Home Assistant Integration
- Inherit from appropriate base classes (CoordinatorEntity, etc.)
- Implement required properties and methods
- Use Home Assistant constants (LawnMowerActivity, etc.)
- Register services correctly

### Logging
- Use structured logging with appropriate levels
- Debug logs for development
- Info logs for important events
- Error logs for failures

## 🚀 Deployment

### Development
- Use `make ha-start` for local development
- Integration automatically linked to Home Assistant
- Debug logs enabled for troubleshooting

### Production
- Copy `custom_components/gardena_smart_system/` to Home Assistant config
- Configure through Home Assistant UI
- Monitor logs for any issues

## 📚 Key Dependencies

### Required Packages
- `aiohttp>=3.7.0` - HTTP client for REST API calls
- `websockets>=10.0` - WebSocket client for real-time updates
- `voluptuous` - Configuration validation
- `dataclasses` - Data models
- `backoff` - Exponential backoff for retries
- `httpx` - Alternative HTTP client (used in SmartSystem)
- `authlib` - OAuth2 client library (used in SmartSystem)

### Home Assistant Dependencies
- `homeassistant.constants` - Home Assistant constants
- `homeassistant.helpers.update_coordinator` - Data coordinator
- `homeassistant.components.lawn_mower` - Lawn mower platform
- `homeassistant.components.valve` - Valve platform

## 🔄 Recent Optimizations

### WebSocket-First Approach
- Eliminated periodic API polling
- Real-time updates via WebSocket
- Reduced API calls by 99.86%
- Improved responsiveness and reliability

### Dynamic Location ID
- WebSocket client retrieves locationId from coordinator
- No hardcoded values
- Supports multiple locations

### Error Handling
- Comprehensive retry logic for API calls
- WebSocket reconnection with exponential backoff
- Graceful degradation on failures

## 🎯 Development Goals

1. **Reliability**: Robust error handling and recovery
2. **Performance**: Minimal API usage, real-time updates
3. **User Experience**: Intuitive Home Assistant integration
4. **Maintainability**: Clean, well-documented code
5. **Extensibility**: Easy to add new device types

## 📞 Support

For issues or questions:
1. Check Home Assistant logs first
2. Verify authentication credentials
3. Test with `make test-auth`
4. Check WebSocket connection status
5. Review API rate limiting

# Rules
Keep the clinerules/application.md and .cursor/rules updated with all relevant information

---

**Last Updated**: August 1, 2025
**Version**: 2.0.0
**Status**: Production Ready with WebSocket Optimization
