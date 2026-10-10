"""API request tracker for Gardena Smart System.

Tracks all outgoing HTTP requests to the Husqvarna/Gardena API to help users
diagnose quota consumption (700 requests/week hard limit).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class APIRequestRecord:
    """A single API request record."""

    timestamp: float
    method: str
    endpoint: str
    status_code: int | None = None
    source: str = ""


class APIRequestTracker:
    """Tracks API requests for diagnostics and quota monitoring."""

    def __init__(self, max_history: int = 200) -> None:
        self._history: Deque[APIRequestRecord] = deque(maxlen=max_history)

    def record(
        self,
        method: str,
        endpoint: str,
        status_code: int | None = None,
        source: str = "",
    ) -> None:
        """Record an API request."""
        self._history.append(
            APIRequestRecord(
                timestamp=time.time(),
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                source=source,
            )
        )

    @property
    def total_requests(self) -> int:
        """Total requests tracked in history."""
        return len(self._history)

    @property
    def requests_this_week(self) -> int:
        """Count requests in the last 7 days."""
        cutoff = time.time() - 7 * 86400
        return sum(1 for r in self._history if r.timestamp >= cutoff)

    @property
    def requests_today(self) -> int:
        """Count requests in the last 24 hours."""
        cutoff = time.time() - 86400
        return sum(1 for r in self._history if r.timestamp >= cutoff)

    @property
    def recent_requests(self) -> list[dict]:
        """Return the last 50 requests as dicts (most recent first)."""
        records = list(self._history)[-50:]
        records.reverse()
        return [
            {
                "timestamp": r.timestamp,
                "method": r.method,
                "endpoint": r.endpoint,
                "status_code": r.status_code,
                "source": r.source,
            }
            for r in records
        ]

    def requests_by_endpoint(self) -> dict[str, int]:
        """Count requests per endpoint in the last 7 days."""
        cutoff = time.time() - 7 * 86400
        counts: dict[str, int] = {}
        for r in self._history:
            if r.timestamp >= cutoff:
                key = f"{r.method} {r.endpoint}"
                counts[key] = counts.get(key, 0) + 1
        return counts
