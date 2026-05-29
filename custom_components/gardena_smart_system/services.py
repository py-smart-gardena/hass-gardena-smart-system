"""Services for controlling Gardena Smart System devices."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
import voluptuous as vol

from .const import DOMAIN
from .coordinator import GardenaSmartSystemCoordinator
from .models import GardenaDevice

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_SCHEMA_BASE = vol.Schema({
    vol.Required("device_id"): cv.string,  # Use string for now, will be validated in service
})

SERVICE_SCHEMA_DURATION = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("duration", default=3600): vol.All(
        cv.positive_int, vol.Range(min=60, max=86400)
    ),
})

SERVICE_SCHEMA_MOWER = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("duration", default=1800): vol.All(
        cv.positive_int, vol.Range(min=60, max=14400)
    ),
})

SERVICE_SCHEMA_VALVE = vol.Schema({
    vol.Optional("device_id"): cv.string,
    vol.Optional("service_id"): cv.string,
    vol.Optional("duration", default=3600): vol.All(
        cv.positive_int, vol.Range(min=60, max=14400)
    ),
})

SERVICE_SCHEMA_VALVE_PAUSE = vol.Schema({
    vol.Optional("device_id"): cv.string,
    vol.Optional("service_id"): cv.string,
    vol.Optional("duration", default=1800): vol.All(
        cv.positive_int, vol.Range(min=60)
    ),
})

SERVICE_SCHEMA_VALVE_BASE = vol.Schema({
    vol.Optional("device_id"): cv.string,
    vol.Optional("service_id"): cv.string,
})

# Command types
class GardenaCommand:
    """Base class for Gardena commands."""
    
    def __init__(self, service_id: str, command_type: str, **kwargs):
        """Initialize command."""
        self.service_id = service_id
        self.command_type = command_type
        self.attributes = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to API format."""
        return {
            "data": {
                "id": f"cmd_{self.service_id}_{self.command_type}",
                "type": self.command_type,
                "attributes": self.attributes,
            }
        }


class MowerCommand(GardenaCommand):
    """Mower-specific commands."""
    
    COMMANDS = {
        "START_SECONDS_TO_OVERRIDE": "Start mowing for specified duration",
        "START_DONT_OVERRIDE": "Start automatic mowing",
        "PARK_UNTIL_NEXT_TASK": "Park and return to charging station",
        "PARK_UNTIL_FURTHER_NOTICE": "Park and ignore schedule",
    }
    
    def __init__(self, service_id: str, command: str, seconds: Optional[int] = None):
        """Initialize mower command."""
        super().__init__(service_id, "MOWER_CONTROL")
        self.attributes["command"] = command
        if seconds and command == "START_SECONDS_TO_OVERRIDE":
            self.attributes["seconds"] = seconds


class PowerSocketCommand(GardenaCommand):
    """Power socket-specific commands."""
    
    COMMANDS = {
        "START_SECONDS_TO_OVERRIDE": "Turn on for specified duration",
        "START_OVERRIDE": "Turn on indefinitely",
        "STOP_UNTIL_NEXT_TASK": "Turn off immediately",
        "PAUSE": "Pause automatic operation",
        "UNPAUSE": "Resume automatic operation",
    }
    
    def __init__(self, service_id: str, command: str, seconds: Optional[int] = None):
        """Initialize power socket command."""
        super().__init__(service_id, "POWER_SOCKET_CONTROL")
        self.attributes["command"] = command
        if seconds and command == "START_SECONDS_TO_OVERRIDE":
            self.attributes["seconds"] = seconds


class ValveCommand(GardenaCommand):
    """Valve-specific commands."""
    
    COMMANDS = {
        "START_SECONDS_TO_OVERRIDE": "Open valve for specified duration",
        "STOP_UNTIL_NEXT_TASK": "Close valve immediately",
        "PAUSE": "Pause automatic operation",
        "UNPAUSE": "Resume automatic operation",
    }
    
    def __init__(self, service_id: str, command: str, seconds: Optional[int] = None):
        """Initialize valve command."""
        super().__init__(service_id, "VALVE_CONTROL")
        self.attributes["command"] = command
        if seconds and command == "START_SECONDS_TO_OVERRIDE":
            self.attributes["seconds"] = seconds
        elif seconds and command == "PAUSE":
            self.attributes["seconds"] = seconds



class GardenaServiceManager:
    """Manager for Gardena device services."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize service manager."""
        self.hass = hass
        self._register_services()
    
    def _register_services(self) -> None:
        """Register all Gardena services."""
        # Mower services
        self.hass.services.async_register(
            DOMAIN,
            "mower_start",
            self._service_mower_start,
            schema=SERVICE_SCHEMA_MOWER,
        )
        self.hass.services.async_register(
            DOMAIN,
            "mower_start_manual",
            self._service_mower_start_manual,
            schema=SERVICE_SCHEMA_MOWER,
        )
        self.hass.services.async_register(
            DOMAIN,
            "mower_park",
            self._service_mower_park,
            schema=SERVICE_SCHEMA_BASE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "mower_park_until_notice",
            self._service_mower_park_until_notice,
            schema=SERVICE_SCHEMA_BASE,
        )
        
        # Power socket services
        self.hass.services.async_register(
            DOMAIN,
            "power_socket_on",
            self._service_power_socket_on,
            schema=SERVICE_SCHEMA_DURATION,
        )
        self.hass.services.async_register(
            DOMAIN,
            "power_socket_on_indefinite",
            self._service_power_socket_on_indefinite,
            schema=SERVICE_SCHEMA_BASE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "power_socket_off",
            self._service_power_socket_off,
            schema=SERVICE_SCHEMA_BASE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "power_socket_pause",
            self._service_power_socket_pause,
            schema=SERVICE_SCHEMA_BASE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "power_socket_unpause",
            self._service_power_socket_unpause,
            schema=SERVICE_SCHEMA_BASE,
        )
        
        # Valve services
        self.hass.services.async_register(
            DOMAIN,
            "valve_open",
            self._service_valve_open,
            schema=SERVICE_SCHEMA_VALVE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "valve_close",
            self._service_valve_close,
            schema=SERVICE_SCHEMA_VALVE_BASE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "valve_pause",
            self._service_valve_pause,
            schema=SERVICE_SCHEMA_VALVE_PAUSE,
        )
        self.hass.services.async_register(
            DOMAIN,
            "valve_unpause",
            self._service_valve_unpause,
            schema=SERVICE_SCHEMA_VALVE_BASE,
        )
        

        # WebSocket services
        self.hass.services.async_register(
            DOMAIN,
            "reconnect_websocket",
            self._service_reconnect_websocket,
        )
        self.hass.services.async_register(
            DOMAIN,
            "websocket_diagnostics",
            self._service_websocket_diagnostics,
            schema=vol.Schema({
                vol.Optional("detailed", default=False): cv.boolean,
            }),
        )

    def _resolve_device_id(self, device_id: str) -> str:
        """Resolve a HA device registry ID to a Gardena device ID.

        The user may pass either:
        - A Home Assistant device registry ID (hex hash like 4bbe526...)
        - A Gardena API device ID (UUID like d8a1faef-...)

        This method checks the device registry first. If the given ID matches
        a registry entry with a Gardena identifier, return the Gardena ID.
        Otherwise assume it's already a Gardena ID and return it as-is.
        """
        registry = dr.async_get(self.hass)
        entry = registry.async_get(device_id)
        if entry:
            for domain, identifier in entry.identifiers:
                if domain == DOMAIN:
                    return identifier
        return device_id

    def _get_coordinator(self, device_id: str) -> Optional[GardenaSmartSystemCoordinator]:
        """Get coordinator for device."""
        for entry_id in self.hass.data[DOMAIN]:
            if entry_id == "service_manager":
                continue
            coordinator = self.hass.data[DOMAIN][entry_id]
            if not hasattr(coordinator, 'get_device_by_id'):
                continue
            device = coordinator.get_device_by_id(device_id)
            if device:
                return coordinator
        return None

    def _get_device_service_id(self, device_id: str, service_type: str) -> Optional[str]:
        """Get service ID for device and service type.

        Only use for device types that have a single service (MOWER, POWER_SOCKET, SENSOR).
        For VALVE, use _resolve_valve_service_id instead.
        """
        coordinator = self._get_coordinator(device_id)
        if not coordinator:
            return None

        device = coordinator.get_device_by_id(device_id)
        if not device or service_type not in device.services:
            return None

        services = device.services[service_type]
        if isinstance(services, list) and len(services) > 0:
            if len(services) > 1:
                _LOGGER.warning(
                    "Device %s has %d %s services, using first one. "
                    "Pass service_id to target a specific service.",
                    device_id, len(services), service_type,
                )
            return services[0].id
        elif hasattr(services, 'id'):
            return services.id
        else:
            return None

    def _resolve_valve_service_id(self, call: ServiceCall) -> Optional[str]:
        """Resolve valve service ID from call data.

        Supports either:
        - service_id directly (e.g. '<device-uuid>:2')
        - device_id (resolves to the single VALVE service, or errors if multiple)
        """
        if (sid := call.data.get("service_id")):
            return sid

        device_id = call.data.get("device_id")
        if not device_id:
            _LOGGER.error("Either device_id or service_id must be provided")
            return None

        device_id = self._resolve_device_id(device_id)
        coordinator = self._get_coordinator(device_id)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_id)
            return None

        device = coordinator.get_device_by_id(device_id)
        if not device or "VALVE" not in device.services:
            _LOGGER.error("No VALVE service found for device %s", device_id)
            return None

        services = device.services["VALVE"]
        if not isinstance(services, list) or len(services) == 0:
            _LOGGER.error("No VALVE service found for device %s", device_id)
            return None

        if len(services) == 1:
            return services[0].id

        _LOGGER.error(
            "Device %s has %d VALVE services; pass service_id to choose one (available: %s)",
            device_id, len(services), [s.id for s in services],
        )
        return None

    async def _send_command(self, service_id: str, command: GardenaCommand) -> bool:
        """Send command to device."""
        coordinator = self._get_coordinator(service_id.split(":")[0] if ":" in service_id else service_id)
        if not coordinator:
            _LOGGER.error("No coordinator found for device")
            return False
        
        try:
            await coordinator.client.send_command(service_id, command.to_dict())
            _LOGGER.debug(f"Command {command.command_type} sent successfully to {service_id}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to send command {command.command_type} to {service_id}: {e}")
            return False

    # Mower services
    async def _service_mower_start(self, call: ServiceCall) -> None:
        """Start automatic mowing."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "MOWER")
        if not service_id:
            _LOGGER.error(f"No MOWER service found for device {device_id}")
            return
        
        command = MowerCommand(service_id, "START_DONT_OVERRIDE")
        await self._send_command(service_id, command)

    async def _service_mower_start_manual(self, call: ServiceCall) -> None:
        """Start manual mowing for specified duration."""
        device_id = self._resolve_device_id(call.data["device_id"])
        duration = call.data["duration"]
        service_id = self._get_device_service_id(device_id, "MOWER")
        if not service_id:
            _LOGGER.error(f"No MOWER service found for device {device_id}")
            return
        
        command = MowerCommand(service_id, "START_SECONDS_TO_OVERRIDE", seconds=duration)
        await self._send_command(service_id, command)

    async def _service_mower_park(self, call: ServiceCall) -> None:
        """Park mower until next task."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "MOWER")
        if not service_id:
            _LOGGER.error(f"No MOWER service found for device {device_id}")
            return
        
        command = MowerCommand(service_id, "PARK_UNTIL_NEXT_TASK")
        await self._send_command(service_id, command)

    async def _service_mower_park_until_notice(self, call: ServiceCall) -> None:
        """Park mower until further notice."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "MOWER")
        if not service_id:
            _LOGGER.error(f"No MOWER service found for device {device_id}")
            return
        
        command = MowerCommand(service_id, "PARK_UNTIL_FURTHER_NOTICE")
        await self._send_command(service_id, command)

    # Power socket services
    async def _service_power_socket_on(self, call: ServiceCall) -> None:
        """Turn on power socket for specified duration."""
        device_id = self._resolve_device_id(call.data["device_id"])
        duration = call.data["duration"]
        service_id = self._get_device_service_id(device_id, "POWER_SOCKET")
        if not service_id:
            _LOGGER.error(f"No POWER_SOCKET service found for device {device_id}")
            return
        
        command = PowerSocketCommand(service_id, "START_SECONDS_TO_OVERRIDE", seconds=duration)
        await self._send_command(service_id, command)

    async def _service_power_socket_on_indefinite(self, call: ServiceCall) -> None:
        """Turn on power socket indefinitely."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "POWER_SOCKET")
        if not service_id:
            _LOGGER.error(f"No POWER_SOCKET service found for device {device_id}")
            return
        
        command = PowerSocketCommand(service_id, "START_OVERRIDE")
        await self._send_command(service_id, command)

    async def _service_power_socket_off(self, call: ServiceCall) -> None:
        """Turn off power socket."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "POWER_SOCKET")
        if not service_id:
            _LOGGER.error(f"No POWER_SOCKET service found for device {device_id}")
            return
        
        command = PowerSocketCommand(service_id, "STOP_UNTIL_NEXT_TASK")
        await self._send_command(service_id, command)

    async def _service_power_socket_pause(self, call: ServiceCall) -> None:
        """Pause power socket operation."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "POWER_SOCKET")
        if not service_id:
            _LOGGER.error(f"No POWER_SOCKET service found for device {device_id}")
            return
        
        command = PowerSocketCommand(service_id, "PAUSE")
        await self._send_command(service_id, command)

    async def _service_power_socket_unpause(self, call: ServiceCall) -> None:
        """Unpause power socket operation."""
        device_id = self._resolve_device_id(call.data["device_id"])
        service_id = self._get_device_service_id(device_id, "POWER_SOCKET")
        if not service_id:
            _LOGGER.error(f"No POWER_SOCKET service found for device {device_id}")
            return
        
        command = PowerSocketCommand(service_id, "UNPAUSE")
        await self._send_command(service_id, command)

    # Valve services
    async def _service_valve_open(self, call: ServiceCall) -> None:
        """Open valve for specified duration."""
        service_id = self._resolve_valve_service_id(call)
        if not service_id:
            return

        duration = call.data["duration"]
        command = ValveCommand(service_id, "START_SECONDS_TO_OVERRIDE", seconds=duration)
        await self._send_command(service_id, command)

    async def _service_valve_close(self, call: ServiceCall) -> None:
        """Close valve."""
        service_id = self._resolve_valve_service_id(call)
        if not service_id:
            return

        command = ValveCommand(service_id, "STOP_UNTIL_NEXT_TASK")
        await self._send_command(service_id, command)

    async def _service_valve_pause(self, call: ServiceCall) -> None:
        """Pause valve operation."""
        service_id = self._resolve_valve_service_id(call)
        if not service_id:
            return

        duration = call.data["duration"]
        command = ValveCommand(service_id, "PAUSE", seconds=duration)
        await self._send_command(service_id, command)

    async def _service_valve_unpause(self, call: ServiceCall) -> None:
        """Unpause valve operation."""
        service_id = self._resolve_valve_service_id(call)
        if not service_id:
            return

        command = ValveCommand(service_id, "UNPAUSE")
        await self._send_command(service_id, command)


    # WebSocket services
    async def _service_reconnect_websocket(self, call: ServiceCall) -> None:
        """Force WebSocket reconnection."""
        _LOGGER.info("WebSocket reconnection service called")

        # Get the first available coordinator (skip service_manager)
        for entry_id in self.hass.data[DOMAIN]:
            if entry_id == "service_manager":
                continue
            entry_data = self.hass.data[DOMAIN][entry_id]
            if hasattr(entry_data, 'websocket_client') and entry_data.websocket_client:
                try:
                    await entry_data.websocket_client.force_reconnect()
                    _LOGGER.info("WebSocket reconnection initiated successfully")
                    return
                except Exception as e:
                    _LOGGER.error(f"Failed to reconnect WebSocket: {e}")

        _LOGGER.error("No WebSocket client found to reconnect")

    async def _service_websocket_diagnostics(self, call: ServiceCall) -> None:
        """Get WebSocket connection diagnostics."""
        detailed = call.data.get("detailed", False)

        for entry_id in self.hass.data[DOMAIN]:
            if entry_id == "service_manager":
                continue
            entry_data = self.hass.data[DOMAIN][entry_id]
            if not hasattr(entry_data, 'websocket_client'):
                continue

            ws_client = entry_data.websocket_client
            if not ws_client:
                _LOGGER.info("WebSocket diagnostics: client not initialized")
                return

            diag = {
                "status": ws_client.connection_status,
                "is_connected": ws_client.is_connected,
                "is_connecting": ws_client.is_connecting,
                "reconnect_attempts": ws_client.reconnect_attempts,
            }

            if detailed:
                diag.update({
                    "websocket_url": ws_client.websocket_url,
                    "shutdown_requested": ws_client._shutdown,
                    "has_listen_task": ws_client.listen_task is not None and not ws_client.listen_task.done() if ws_client.listen_task else False,
                    "has_reconnect_task": ws_client.reconnect_task is not None and not ws_client.reconnect_task.done() if ws_client.reconnect_task else False,
                })

            _LOGGER.info(f"WebSocket diagnostics: {diag}")
            return
