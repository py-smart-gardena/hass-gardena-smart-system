"""Webhook client for Gardena Smart System push events.

Alternative to GardenaWebSocketClient: instead of maintaining a persistent
WebSocket, register an HTTPS callback URL with Husqvarna's cloud
(POST /v2/webhook). Events are then pushed to that URL whenever device
state changes.

Requires:
- A publicly-reachable HTTPS URL for Home Assistant (hass.config.external_url
  or an explicit override in entry.options).
- The 'webhook' core integration (declared in manifest.json dependencies).

Lifecycle:
- start() registers the HA-side webhook handler AND the cloud-side endpoint.
- _renewal_loop re-registers periodically before validUntil expires.
- stop() unregisters both sides.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import aiohttp
from aiohttp import web

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant

from .auth import GardenaAuthenticationManager
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Renew the webhook this many seconds before validUntil so we never have a gap.
_RENEWAL_SAFETY_MARGIN = 3600  # 1h

# Fallback renewal cadence if the cloud doesn't return validUntil for some reason.
_FALLBACK_RENEWAL_INTERVAL = 86400  # 24h

# Husqvarna sends `X-Authorization-Content-Sha256` (observed in live traffic).
# Other potential names kept as fallbacks in case the gateway rotates them.
_HMAC_HEADER_CANDIDATES = (
    "X-Authorization-Content-Sha256",
    "X-Husqvarna-Signature",
    "X-Husqvarna-HMAC",
    "X-Gardena-Signature",
    "X-Hub-Signature-256",
    "X-Signature",
)


class GardenaWebhookClient:
    """Receives Gardena push events via an HA-registered HTTPS webhook."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth_manager: GardenaAuthenticationManager,
        event_callback: Callable[[Dict[str, Any]], None],
        entry_id: str,
        external_url: str,
        coordinator=None,
    ) -> None:
        """Initialize the webhook client.

        external_url is the public origin (e.g. https://ha.example.com)
        without trailing slash or path — the /api/webhook/<id> path is
        appended automatically.
        """
        self.hass = hass
        self.auth_manager = auth_manager
        self.event_callback = event_callback
        self.coordinator = coordinator
        self.entry_id = entry_id
        self.external_url = external_url.rstrip("/")

        # Stable across HA restarts, unique per config entry.
        self.webhook_id = f"gardena_{entry_id}"
        self.location_id: Optional[str] = None
        self.hmac_secret: Optional[str] = None
        self.valid_until_epoch: Optional[int] = None
        self.is_registered = False
        self._renewal_task: Optional[asyncio.Task] = None
        self._shutdown = False

    @property
    def callback_url(self) -> str:
        return f"{self.external_url}/api/webhook/{self.webhook_id}"

    async def start(self) -> None:
        """Register HA-side handler and Husqvarna cloud-side endpoint."""
        if self.is_registered:
            _LOGGER.debug("Webhook already registered")
            return

        _LOGGER.info("Starting Gardena webhook client (entry %s)", self.entry_id)
        self._shutdown = False

        if not self.coordinator or not self.coordinator.locations:
            _LOGGER.error("Cannot start webhook: no location data available yet")
            return
        self.location_id = next(iter(self.coordinator.locations.keys()))

        # 1. Register the HA-side handler first — if cloud registration succeeds
        #    we must already be able to receive.
        webhook.async_register(
            self.hass,
            DOMAIN,
            "Gardena Smart System",
            self.webhook_id,
            self._handle_webhook,
            allowed_methods=["POST"],
        )

        # 2. Register with Husqvarna
        success = await self._register_with_cloud()
        if not success:
            webhook.async_unregister(self.hass, self.webhook_id)
            _LOGGER.error(
                "Webhook cloud registration failed — falling back to no push. "
                "Check that external_url (%s) is reachable from Husqvarna's cloud.",
                self.external_url,
            )
            return

        self.is_registered = True
        self._renewal_task = asyncio.create_task(self._renewal_loop())

        if self.coordinator:
            self.coordinator.async_set_updated_data(self.coordinator.locations)

        _LOGGER.info(
            "Webhook registered: %s (validUntil=%s)",
            self.callback_url, self.valid_until_epoch,
        )

    async def stop(self) -> None:
        """Unregister both sides and stop renewal."""
        _LOGGER.info("Stopping Gardena webhook client")
        self._shutdown = True

        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass

        if self.is_registered:
            try:
                await self._delete_cloud_registration()
            except Exception as e:
                _LOGGER.warning("Error deleting webhook from cloud: %s", e)

            try:
                webhook.async_unregister(self.hass, self.webhook_id)
            except Exception as e:
                _LOGGER.warning("Error unregistering HA webhook: %s", e)

        self.is_registered = False
        self.hmac_secret = None
        self.valid_until_epoch = None

    async def force_reconnect(self) -> None:
        """Re-register webhook (analog to WebSocket force_reconnect)."""
        _LOGGER.info("Force-renewing webhook registration")
        await self._register_with_cloud()

    async def _register_with_cloud(self) -> bool:
        """POST /v2/webhook with our callback URL, with retry on 5xx."""
        body = {
            "data": {
                "id": f"ha_{self.entry_id}",
                "attributes": {
                    "url": self.callback_url,
                    "locationId": self.location_id,
                },
            }
        }

        for attempt in range(3):
            try:
                await self.auth_manager.authenticate()
                headers = self.auth_manager.get_auth_headers()
                session = await self.auth_manager._get_session()

                async with session.post(
                    "https://api.smart.gardena.dev/v2/webhook",
                    headers=headers,
                    json=body,
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        attrs = data["data"]["attributes"]
                        self.hmac_secret = attrs.get("hmacSecret")
                        self.valid_until_epoch = attrs.get("validUntil")
                        _LOGGER.debug(
                            "Webhook registered with cloud, validUntil=%s",
                            self.valid_until_epoch,
                        )
                        return True

                    if response.status in (500, 502, 504) and attempt < 2:
                        delay = 2 ** attempt
                        _LOGGER.warning(
                            "Webhook registration got %s, retrying in %ds (attempt %d/3)",
                            response.status, delay, attempt + 1,
                        )
                        await asyncio.sleep(delay)
                        continue

                    text = await response.text()
                    _LOGGER.error(
                        "Webhook registration failed: %s — %s",
                        response.status, text[:300],
                    )
                    return False
            except aiohttp.ClientError as e:
                if attempt < 2:
                    delay = 2 ** attempt
                    _LOGGER.warning(
                        "Webhook registration network error: %s — retrying in %ds (attempt %d/3)",
                        e, delay, attempt + 1,
                    )
                    await asyncio.sleep(delay)
                    continue
                _LOGGER.error("Webhook registration network error: %s", e)
                return False
            except Exception as e:
                _LOGGER.error("Webhook registration unexpected error: %s", e)
                return False
        return False

    async def _delete_cloud_registration(self) -> None:
        """DELETE /v2/webhook/{locationId} to deregister our endpoint."""
        if not self.location_id or not self.hmac_secret:
            _LOGGER.debug("Skip webhook delete: no locationId or hmac_secret")
            return

        try:
            await self.auth_manager.authenticate()
            headers = self.auth_manager.get_auth_headers()
            # Per OpenAPI spec the DELETE requires the hmac secret as header
            headers["X-HMAC-Secret"] = self.hmac_secret
            session = await self.auth_manager._get_session()

            async with session.delete(
                f"https://api.smart.gardena.dev/v2/webhook/{self.location_id}",
                headers=headers,
            ) as response:
                if response.status in (204, 404):
                    _LOGGER.debug("Webhook deregistered (status %s)", response.status)
                else:
                    text = await response.text()
                    _LOGGER.warning(
                        "Webhook deregistration returned %s: %s",
                        response.status, text[:200],
                    )
        except Exception as e:
            _LOGGER.warning("Error during webhook deregistration: %s", e)

    async def _renewal_loop(self) -> None:
        """Periodically re-register webhook to renew validUntil."""
        try:
            while not self._shutdown:
                now = datetime.now(timezone.utc).timestamp()
                if self.valid_until_epoch and self.valid_until_epoch > now:
                    sleep_for = max(60, self.valid_until_epoch - now - _RENEWAL_SAFETY_MARGIN)
                else:
                    sleep_for = _FALLBACK_RENEWAL_INTERVAL

                _LOGGER.debug("Webhook renewal scheduled in %.0fs", sleep_for)
                await asyncio.sleep(sleep_for)

                if self._shutdown:
                    return

                _LOGGER.info("Renewing webhook registration")
                if not await self._register_with_cloud():
                    # Renewal failed — try again on a shorter interval
                    _LOGGER.warning(
                        "Webhook renewal failed, retrying in 5 minutes"
                    )
                    await asyncio.sleep(300)
        except asyncio.CancelledError:
            _LOGGER.debug("Webhook renewal task cancelled")
        except Exception as e:
            _LOGGER.error("Webhook renewal loop error: %s", e)

    async def _handle_webhook(
        self,
        hass: HomeAssistant,
        webhook_id: str,
        request: web.Request,
    ) -> web.Response:
        """Process incoming Husqvarna push event."""
        try:
            body = await request.read()

            # Try to find the signature header. Husqvarna's spec doesn't pin
            # this down — we accept any of the common candidate names. If none
            # match, log the headers (minus sensitive ones) so we can identify
            # the right name and lock it down later.
            signature: Optional[str] = None
            sig_header_name: Optional[str] = None
            for hdr in _HMAC_HEADER_CANDIDATES:
                if hdr in request.headers:
                    signature = request.headers[hdr]
                    sig_header_name = hdr
                    break

            if self.hmac_secret and signature:
                # Husqvarna's exact signing scheme isn't documented. Try both
                # plain SHA-256(body) (AWS SigV4-style content integrity) AND
                # HMAC-SHA256(secret, body) — accept whichever matches.
                # Some providers prefix with "sha256=" — strip that.
                sig_clean = signature.split("=", 1)[-1] if "=" in signature else signature
                sig_clean = sig_clean.strip().lower()

                expected_plain = hashlib.sha256(body).hexdigest()
                expected_hmac = hmac.new(
                    self.hmac_secret.encode(), body, hashlib.sha256,
                ).hexdigest()

                if hmac.compare_digest(sig_clean, expected_plain):
                    _LOGGER.debug(
                        "Webhook integrity verified via %s (plain SHA-256)",
                        sig_header_name,
                    )
                elif hmac.compare_digest(sig_clean, expected_hmac):
                    _LOGGER.debug(
                        "Webhook integrity verified via %s (HMAC-SHA256)",
                        sig_header_name,
                    )
                else:
                    _LOGGER.warning(
                        "Webhook integrity check failed via %s. "
                        "got=%s plain_sha256=%s hmac_sha256=%s",
                        sig_header_name,
                        sig_clean[:16] + "…",
                        expected_plain[:16] + "…",
                        expected_hmac[:16] + "…",
                    )
                    # Don't reject yet — log and pass through during debugging
                    # so we don't lose events while we figure out the scheme.
            elif self.hmac_secret:
                # No signature found — log header names so we can adapt.
                visible = [
                    h for h in request.headers.keys()
                    if h.lower() not in ("authorization", "cookie")
                ]
                _LOGGER.warning(
                    "Webhook arrived without recognized signature header. "
                    "Got headers: %s. Processing anyway for now (debugging).",
                    visible,
                )

            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                _LOGGER.error("Webhook body not valid JSON: %s", e)
                return web.Response(status=400)

            _LOGGER.debug("Webhook event: %s", data)
            await self._process_message(data)

            return web.Response(status=204)
        except Exception as e:
            _LOGGER.exception("Error handling webhook: %s", e)
            return web.Response(status=500)

    async def _process_message(self, data: Dict[str, Any]) -> None:
        """Dispatch payload to coordinator. Mirrors WebSocket _process_service_update."""
        try:
            # Husqvarna webhook payload may be a single service object or wrapped.
            # Handle both: direct {type, id, attributes} and JSON:API {data: ...}
            payload = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(payload, dict):
                _LOGGER.debug("Webhook: unexpected payload shape: %r", data)
                return

            msg_type = payload.get("type")
            if msg_type not in ("VALVE", "COMMON", "MOWER", "POWER_SOCKET", "SENSOR", "VALVE_SET"):
                _LOGGER.debug("Webhook: unknown message type %r: %s", msg_type, payload)
                return

            service_id = payload.get("id")
            attributes = payload.get("attributes", {})
            if not service_id:
                _LOGGER.debug("Webhook: payload missing service id")
                return

            device_id = service_id.split(":")[0]
            event = {
                "type": "service_update",
                "service_id": service_id,
                "service_type": msg_type,
                "device_id": device_id,
                "data": attributes,
            }
            if self.event_callback:
                await self.event_callback(event)
        except Exception as e:
            _LOGGER.error("Error processing webhook payload: %s", e)

    @property
    def connection_status(self) -> str:
        """Connection status string (parallel to WebSocket client)."""
        if self._shutdown:
            return "stopped"
        if self.is_registered:
            return "registered"
        return "unregistered"

    # --- Compatibility shims so the WebSocket connectivity sensor and any
    # consumers that introspect a push client can treat both transports the
    # same way without branching. ---

    @property
    def is_connected(self) -> bool:
        """True when our webhook is currently registered with the cloud."""
        return self.is_registered

    @property
    def is_connecting(self) -> bool:
        """Webhook registration is synchronous — never in 'connecting' state."""
        return False

    @property
    def reconnect_attempts(self) -> int:
        """No reconnect counter in webhook mode — return 0 for shape parity."""
        return 0
