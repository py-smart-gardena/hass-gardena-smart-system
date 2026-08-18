# AGENTS.md — Gardena Smart System HA Integration

## Project Overview

Home Assistant custom integration for Gardena Smart System devices (mowers, valves, sensors, power sockets).
Uses Gardena API v2 (REST + WebSocket) with OAuth2 via Husqvarna authentication.

Two separate repos live under `py-smart-gardena/`:
- `hass-gardena-smart-system/` — this HA integration (custom component)
- `py-smart-gardena/` — lower-level Python library (legacy, not used by this integration)

## Architecture

```
__init__.py          Entry point: async_setup_entry
config_flow.py       UI configuration flow (client_id / client_secret)
auth.py              OAuth2 token manager (client credentials grant, auto-refresh)
gardena_client.py    REST API client (initial data load: /locations)
coordinator.py       DataUpdateCoordinator: owns locations data, starts WebSocket
websocket_client.py  Persistent WebSocket connection, real-time device updates
models.py            Data models: GardenaLocation, GardenaDevice, GardenaService
entities.py          Base entity class (CoordinatorEntity)
lawn_mower.py        LawnMowerEntity (SILENO)
valve.py             ValveEntity
switch.py            SwitchEntity (power sockets)
sensor.py            SensorEntity (temperature, humidity, light, battery)
binary_sensor.py     BinarySensorEntity (connectivity)
```

API call budget: **2 calls/day** (1 auth + 1 `/locations` at startup). All state updates come via WebSocket. Never add polling.

## Critical Rules — Home Assistant Asyncio

**Never call blocking functions directly in the event loop.** HA detects and reports these as errors.

Blocking operations that MUST run in an executor:
- `ssl.create_default_context()` — calls `load_default_certs` + `set_default_verify_paths`
- Any file I/O, `socket` calls, or CPU-heavy work

Pattern to use:
```python
# Wrong
ssl_context = ssl.create_default_context()

# Correct
ssl_context = await asyncio.get_event_loop().run_in_executor(None, ssl.create_default_context)
```

Or via HA helper: `await hass.async_add_executor_job(blocking_fn, *args)`

All methods in this integration must be `async`. All I/O uses `aiohttp` (REST) or `websockets` (WS).

## Authentication

- Flow: `POST /v1/oauth2/token` with `grant_type=client_credentials`
- Token is refreshed automatically 5 minutes before expiry
- Headers required on every API request:
  ```
  Authorization: Bearer <token>
  Authorization-Provider: husqvarna
  X-Api-Key: <client_id>
  Content-Type: application/vnd.api+json
  ```
- `GARDENA_DEV_MODE=true` bypasses SSL verification (macOS dev only via `make ha-start`) — never hardcode `dev_mode=True` in setup

## Development Commands

```bash
make setup       # Create venv + install deps
make test        # Run all unit tests (pytest)
make test-auth   # Authentication tests only
make test-real   # Live test against real API (needs env vars)
make clean       # Remove venv, caches, build artifacts

make ha-start    # Start local HA instance (http://localhost:8123)
make ha-stop     # Stop local HA
make ha-logs     # Tail HA logs
make ha-reset    # Wipe local HA config
```

Required env vars for real tests:
```bash
export GARDENA_CLIENT_ID=...
export GARDENA_CLIENT_SECRET=...
```

## Testing

- Test files live alongside source in `custom_components/gardena_smart_system/test_*.py`
- pytest config: `pytest.ini` — asyncio_mode=auto, coverage enabled, sockets disabled
- Run a single file: `venv/bin/pytest custom_components/gardena_smart_system/test_websocket.py -v`
- Tests are unit tests by default; integration tests marked with `@pytest.mark.integration`

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `Detected blocking call` in HA logs | Synchronous stdlib call in async context | Wrap with `run_in_executor` |
| 429 Too Many Requests | Polling or duplicate API calls | Use WebSocket; never add periodic refresh |
| Entity not appearing | Missing COMMON service or wrong unique_id | Check `models.py` service parsing |
| WebSocket not reconnecting | `_shutdown=True` set prematurely | Check `stop()` call path in coordinator |
| Token expired mid-session | Token refresh not triggered | `auth.py` refreshes 5min before expiry; check clock skew |

## Code Conventions

- All I/O is `async/await`
- Use `_LOGGER = logging.getLogger(__name__)` in each module
- Log levels: `debug` for state transitions, `info` for connect/disconnect, `error` for failures
- No sensitive data (tokens, secrets) in logs
- Branch names: `fix/<short-description>` or `feat/<short-description>`
- Commit style: `fix:` / `feat:` / `refactor:` prefix, imperative mood
