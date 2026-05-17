"""WebSocket client for Gardena Smart System real-time events."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .auth import GardenaAuthenticationManager
from .const import (
    DOMAIN,
    WEBSOCKET_RECONNECT_DELAY,
    WEBSOCKET_MAX_RECONNECT_DELAY,
    WEBSOCKET_IDLE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class GardenaWebSocketClient:
    """WebSocket client for Gardena Smart System real-time events."""

    def __init__(
        self,
        auth_manager: GardenaAuthenticationManager,
        event_callback: Callable[[Dict[str, Any]], None],
        hass=None,
        coordinator=None,
    ) -> None:
        """Initialize the WebSocket client."""
        self.auth_manager = auth_manager
        self.event_callback = event_callback
        self.hass = hass
        self.coordinator = coordinator
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.websocket_url: Optional[str] = None
        self.is_connected = False
        self.is_connecting = False
        self.reconnect_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.reconnect_attempts = 0
        self._shutdown = False

    async def start(self) -> None:
        """Start the WebSocket client."""
        if self.is_connected or self.is_connecting:
            _LOGGER.debug("WebSocket client already running")
            return

        _LOGGER.info("Starting Gardena WebSocket client")
        self._shutdown = False
        await self._connect()

    async def stop(self) -> None:
        """Stop the WebSocket client."""
        _LOGGER.info("Stopping Gardena WebSocket client")
        self._shutdown = True
        
        # Cancel running tasks
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.is_connected = False
        self.is_connecting = False
        self.reconnect_attempts = 0

    async def force_reconnect(self) -> None:
        """Force a reconnection attempt."""
        if self._shutdown:
            return
        
        _LOGGER.info("Forcing WebSocket reconnection")
        self.reconnect_attempts = 0  # Reset attempts
        self.is_connected = False
        self.is_connecting = False
        
        # Cancel any existing reconnect task
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            self.reconnect_task = None
        
        # Start fresh connection
        await self._connect()

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        if self.is_connecting:
            return
        
        self.is_connecting = True
        
        try:
            # Get WebSocket URL
            await self._get_websocket_url()
            
            if not self.websocket_url:
                _LOGGER.error("Failed to get WebSocket URL")
                self.is_connecting = False
                await self._schedule_reconnect()
                return
            
            # Connect to WebSocket
            _LOGGER.debug(f"Connecting to WebSocket: {self.websocket_url}")
            
            # Handle SSL issues on macOS in development
            ssl_context = None
            if self.auth_manager._dev_mode:
                import ssl
                ssl_context = await asyncio.get_event_loop().run_in_executor(
                    None, ssl.create_default_context
                )
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=30,
                ping_timeout=10,
                ssl=ssl_context,
            )
            
            self.is_connected = True
            self.is_connecting = False
            self.reconnect_attempts = 0
            
            _LOGGER.info("WebSocket connected successfully")
            
            # Start listening for messages
            self.listen_task = asyncio.create_task(self._listen_for_messages())
            
            # Notify coordinator of status change
            if self.coordinator:
                self.coordinator.async_set_updated_data(self.coordinator.locations)
            
        except Exception as e:
            _LOGGER.error(f"Failed to connect to WebSocket: {e}")
            self.is_connected = False
            self.is_connecting = False
            await self._schedule_reconnect()

    async def _get_websocket_url(self) -> None:
        """Get WebSocket URL from Gardena API with retry on transient server errors."""
        # Resolve location_id once — same logic as before.
        location_id = None
        if self.coordinator and self.coordinator.locations:
            location_id = list(self.coordinator.locations.keys())[0]
            _LOGGER.debug(f"Using location ID from coordinator: {location_id}")
        else:
            _LOGGER.warning("No locations available in coordinator, using fallback location ID")
            location_id = "2188c99e-df0d-4bb9-8273-71415fa70569"

        # Retry on 500/502/504. Husqvarna's gateway intermittently returns 504s
        # — without retry here, every reconnect attempt during such a window
        # fails permanently and the integration eventually gives up.
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                await self.auth_manager.authenticate()
                headers = self.auth_manager.get_auth_headers()
                session = await self.auth_manager._get_session()

                async with session.post(
                    "https://api.smart.gardena.dev/v2/websocket",
                    headers=headers,
                    json={
                        "data": {
                            "type": "WEBSOCKET",
                            "attributes": {"locationId": location_id},
                        }
                    },
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        self.websocket_url = data["data"]["attributes"]["url"]
                        _LOGGER.debug(f"WebSocket URL obtained: {self.websocket_url}")
                        return
                    if response.status in (500, 502, 504) and attempt < max_attempts - 1:
                        delay = 2 ** attempt
                        _LOGGER.warning(
                            "Server error %s getting WebSocket URL, retrying in %ds "
                            "(attempt %d/%d)",
                            response.status, delay, attempt + 1, max_attempts,
                        )
                        await asyncio.sleep(delay)
                        continue
                    _LOGGER.error(f"Failed to get WebSocket URL: {response.status}")
                    self.websocket_url = None
                    return
            except Exception as e:
                if attempt < max_attempts - 1:
                    delay = 2 ** attempt
                    _LOGGER.warning(
                        "Error getting WebSocket URL: %s — retrying in %ds (attempt %d/%d)",
                        e, delay, attempt + 1, max_attempts,
                    )
                    await asyncio.sleep(delay)
                    continue
                _LOGGER.error(f"Error getting WebSocket URL: {e}")
                self.websocket_url = None
                return

    def _get_websocket_headers(self) -> Dict[str, str]:
        """Get headers for WebSocket connection."""
        return {
            "Authorization-Provider": "husqvarna",
            "X-Api-Key": self.auth_manager.client_id,
        }

    async def _listen_for_messages(self) -> None:
        """Listen for WebSocket messages with an idle-timeout watchdog.

        Library-level ping/pong (websockets.connect ping_interval) only catches
        TCP/protocol failures. Half-open connections (Husqvarna load-balancer
        switch without FIN, network silent-drop) can leave a socket that
        accepts pongs but delivers no app data — symptom we saw: 12h stale
        without reconnect trigger. The wait_for here forces reconnect after
        WEBSOCKET_IDLE_TIMEOUT seconds without any incoming message.
        """
        try:
            while not self._shutdown:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), timeout=WEBSOCKET_IDLE_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "WebSocket idle for %ds without messages — forcing reconnect",
                        WEBSOCKET_IDLE_TIMEOUT,
                    )
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                    break

                try:
                    data = json.loads(message)
                    _LOGGER.debug(f"Received WebSocket message: {data}")
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    _LOGGER.error(f"Error processing WebSocket message: {e}")

        except ConnectionClosed:
            _LOGGER.info("WebSocket connection closed, will reconnect")
        except WebSocketException as e:
            _LOGGER.error(f"WebSocket error: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected WebSocket error: {e}")
        finally:
            self.is_connected = False
            if not self._shutdown:
                await self._schedule_reconnect()

            # Notify coordinator of status change
            if self.coordinator:
                self.coordinator.async_set_updated_data(self.coordinator.locations)

    async def _process_message(self, data: Dict[str, Any]) -> None:
        """Process received WebSocket message."""
        try:
            # Check if it's a ping message
            if "data" in data and "type" in data["data"] and data["data"]["type"] == "WEBSOCKET_PING":
                await self._send_pong()
                return
            
            # Check if it's a service update message (direct service data)
            if "type" in data and data["type"] in ["VALVE", "COMMON", "MOWER", "POWER_SOCKET", "SENSOR", "VALVE_SET"]:
                await self._process_service_update(data)
            else:
                _LOGGER.debug(f"Received unknown message type: {data}")
                
        except Exception as e:
            _LOGGER.error(f"Error processing WebSocket message: {e}")

    async def _process_service_update(self, service_data: Dict[str, Any]) -> None:
        """Process service update from WebSocket."""
        try:
            # Extract service information
            service_id = service_data.get("id")
            service_type = service_data.get("type")
            attributes = service_data.get("attributes", {})
            
            if not service_id:
                _LOGGER.debug("Service update missing service_id")
                return
            
            # Extract device_id from service_id (remove suffixes like :1, :2, etc.)
            device_id = service_id.split(":")[0]
            
            _LOGGER.debug(f"Processing service update: service_id={service_id}, device_id={device_id}, type={service_type}")
            
            # Create event for callback
            event = {
                "type": "service_update",
                "service_id": service_id,
                "service_type": service_type,
                "device_id": device_id,
                "data": attributes,
            }
            
            # Call the event callback
            if self.event_callback:
                await self.event_callback(event)
                
        except Exception as e:
            _LOGGER.error(f"Error processing service update: {e}")

    async def _process_device_event(self, event_data: Dict[str, Any]) -> None:
        """Process device event from WebSocket."""
        try:
            # Extract device and service information
            if "attributes" in event_data:
                attributes = event_data["attributes"]
                
                # Create event for callback
                event = {
                    "type": "device_event",
                    "data": attributes,
                    "timestamp": attributes.get("timestamp"),
                }
                
                # Call the event callback
                if self.event_callback:
                    await self.event_callback(event)
                    
        except Exception as e:
            _LOGGER.error(f"Error processing device event: {e}")

    async def _send_pong(self) -> None:
        """Send pong response to ping."""
        try:
            if self.websocket and self.is_connected:
                pong_message = {
                    "data": {
                        "type": "WEBSOCKET_PONG",
                        "attributes": {}
                    }
                }
                await self.websocket.send(json.dumps(pong_message))
                _LOGGER.debug("Sent pong response")
        except Exception as e:
            _LOGGER.error(f"Error sending pong: {e}")

    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt with capped exponential backoff.

        Never gives up: the previous behaviour stopped trying after
        WEBSOCKET_MAX_RECONNECT_ATTEMPTS (10), which left the integration
        permanently disconnected when Husqvarna's cloud was unresponsive for
        more than ~10 min. Now retries forever, with delay capped at
        WEBSOCKET_MAX_RECONNECT_DELAY so we don't hammer the API.
        """
        if self._shutdown:
            return

        # Cancel any existing reconnect task
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass

        self.reconnect_attempts += 1

        if self.reconnect_attempts == 4:
            _LOGGER.warning(
                "WebSocket reconnection taking longer than expected (attempt %d)",
                self.reconnect_attempts,
            )
        elif self.reconnect_attempts == 20:
            _LOGGER.error(
                "WebSocket still disconnected after %d attempts — check Husqvarna API status",
                self.reconnect_attempts,
            )

        # Use shorter delays for the first few attempts (likely token renewal),
        # then exponential backoff capped at WEBSOCKET_MAX_RECONNECT_DELAY.
        if self.reconnect_attempts <= 3:
            delay = 5
        else:
            delay = min(
                WEBSOCKET_RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 4)),
                WEBSOCKET_MAX_RECONNECT_DELAY,
            )

        _LOGGER.debug(
            f"Scheduling reconnection attempt {self.reconnect_attempts} in {delay} seconds"
        )

        self.reconnect_task = asyncio.create_task(self._delayed_reconnect(delay))

    async def _delayed_reconnect(self, delay: int) -> None:
        """Delayed reconnection attempt."""
        try:
            _LOGGER.debug(f"Waiting {delay} seconds before reconnection attempt")
            await asyncio.sleep(delay)
            if not self._shutdown:
                _LOGGER.debug("Starting reconnection attempt")
                await self._connect()
            else:
                _LOGGER.debug("WebSocket shutdown during delay, not reconnecting")
        except asyncio.CancelledError:
            _LOGGER.debug("Reconnection task cancelled")
        finally:
            self.reconnect_task = None

    @property
    def connection_status(self) -> str:
        """Get connection status."""
        if self._shutdown:
            return "stopped"
        elif self.is_connected:
            return "connected"
        elif self.is_connecting:
            return "connecting"
        else:
            return "disconnected"
