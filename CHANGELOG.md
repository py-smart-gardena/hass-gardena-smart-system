# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [3.0.6] - 2026-05-27

### Added

- Reconfigure config flow to update Husqvarna Application Key and Client Secret without removing the integration (#372)
- Clearer 429 rate-limit error handling during credential validation

### Fixed

- WebSocket reconnection now uses conservative exponential backoff (30s, 60s, 120s... up to 15min) instead of aggressive 5s retries that burned through the Gardena API quota of 700 req/week (#370)
- WebSocket URL request (`POST /v2/websocket`) now handles 429 responses and respects `Retry-After` header instead of blindly retrying (#370)

## [3.0.5] - 2026-05-24

### Fixed

- Valve entities no longer log their state twice on every update — activity logging moved out of property getters (called multiple times per update cycle by Home Assistant) into the coordinator-update callback, with state-transition deduplication. Resolves HA's internal rate limiter triggering after 200+ messages on installations with several valves (#371)

## [3.0.4] - 2026-05-19

### Fixed

- `mower_error` sensor now returns `no_message` for informational operational states instead of surfacing them as errors. The following states no longer trigger error-based automations: `parked_daily_limit_reached`, `outside_working_area`, `off_disabled`, `off_hatch_open`, `off_hatch_closed`, `wait_updating`, `wait_power_up`, `wait_stop_pressed`, `wait_for_safety_pin`, `guide_calibration_accomplished`, `connection_changed`, `connection_not_changed`, `uninitialised` (#365)

## [3.0.3] - 2026-05-19

### Fixed

- Fix automation hang when valve open command receives a temporary 504 error — retry logic no longer deadlocks on the internal request lock (#366)

## [3.0.2] - 2026-05-18

### Fixed

- Fix lawn mower never showing "Returning" state — `OK_SEARCHING` was incorrectly mapped to `MOWING` instead of `RETURNING` (#363)

## [3.0.1] - 2026-05-13

### Fixed

- Fix ImportError for `UnitOfIlluminance` on older HA versions (#356)

## [3.0.0] - 2026-05-13

### Breaking Changes

- **WebSocket Status entity migrated from `sensor` to `binary_sensor`** — The old `sensor.gardena_websocket_status` entity is removed. A new `binary_sensor.gardena_websocket_connected` entity with device class `connectivity` replaces it. Automations using the old entity must be updated.

### Added

- English translations for all mower error codes from the Gardena API v2
- German translations for all mower error codes and updated config/services translations (#347)

### Fixed

- Mower error code sensor showing "Unknown" when there is no error (#347)
- Light intensity sensor using invalid unit "lux" instead of "lx" for illuminance device class (#351)
- WebSocket disconnection no longer logs a warning on transient network interruptions (#352)

## [2.1.0] - 2026-05-11

### Added

- Support removal of orphaned devices via `async_remove_config_entry_device` (#346)

## [2.0.9] - 2026-05-11

### Fixed

- Mower error code sensor showing "Unknown" when there is no error (#347)
- Complete list of recognized mower error codes to match Gardena API v2

## [2.0.8] - 2026-05-11

### Removed

- "Measure Now" button and `sensor_measure` service — the `SENSOR_CONTROL` command type does not exist in the Gardena API v2 (#345)

## [2.0.7] - 2026-05-09

### Added

- Operating hours and RF link quality as dedicated sensor entities (#344)

## [2.0.6] - 2026-05-08

### Fixed

- Resolve HA device_id to Gardena UUID in services and fix API command format (#342, #343)

## [2.0.5] - 2026-05-07

### Fixed

- Retry on HTTP 504 gateway timeout from Gardena API (#309)
- Make WebSocket status sensor unique_id unique per config entry
- Handle HTTP 429 rate limiting with retry and clear error message

### Added

- Watering remaining time sensor for valves (#167)
- `state_class` to sensors for long-term statistics support

## [2.0.4] - 2026-05-05

### Fixed

- Use MOISTURE device class for soil humidity sensor (#339)

## [2.0.3] - 2026-05-04

### Fixed

- Add missing mower activity states

## [2.0.2] - 2026-05-01

### Fixed

- Initial stable release of v2 rewrite

## [2.0.1] - 2026-04-28

### Fixed

- Beta fixes and stabilization
