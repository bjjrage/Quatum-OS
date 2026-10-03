"""Private user-stream manager: bounded backoff reconnect, health, normalized events.

Websocket state is never authoritative: REST reconciliation remains the recovery mechanism.
The connector is injected (no network in tests); without credentials the stream is NOT_CONFIGURED.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.security import CONFIGURED


def backoff_delay(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    return min(cap, base * (2 ** max(0, attempt - 1)))


class PrivateStreamManager:
    def __init__(self, adapter, handler: Callable[[Dict[str, Any]], None], connector: Any = None,
                 base_delay: float = 1.0, max_delay: float = 60.0, max_attempts: int = 8,
                 clock_ns: Callable[[], int] = time.time_ns, sleep: Callable[[float], None] = time.sleep,
                 on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.adapter, self.handler, self.connector = adapter, handler, connector
        self.base_delay, self.max_delay, self.max_attempts = base_delay, max_delay, max_attempts
        self._clock_ns, self._sleep, self._on_event = clock_ns, sleep, on_event
        self.state = "DISCONNECTED"
        self.reconnect_count = 0
        self.consecutive_failures = 0
        self.last_event_ns: Optional[int] = None
        self.last_error: Optional[str] = None
        self.delays: List[float] = []

    def _credentials_ok(self) -> bool:
        creds = getattr(self.adapter, "credentials", None)
        if creds is None:  # fake / test adapters
            return True
        return creds.status(self.adapter.venue, self.adapter.environment)["status"] == CONFIGURED

    def _emit(self, kind: str, **kw):
        if self._on_event:
            self._on_event(kind, kw)

    def connect(self) -> bool:
        if not self._credentials_ok():
            self.state = "NOT_CONFIGURED"
            return False
        if self.connector is None:
            self.state = "NO_CONNECTOR"
            return False
        self.state = "CONNECTING"
        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            try:
                self.connector.connect()
                self.state = "CONNECTED"
                self.consecutive_failures = 0
                self._emit("CONNECTED", attempt=attempt)
                return True
            except Exception as e:
                self.consecutive_failures += 1
                self.last_error = type(e).__name__  # no message: may contain secrets
                d = backoff_delay(attempt, self.base_delay, self.max_delay)
                self.delays.append(d)
                self.state = "BACKOFF"
                self._emit("CONNECT_FAILED", attempt=attempt, next_delay_s=d)
                self._sleep(d)
        self.state = "FAILED"
        self._emit("CONNECT_GAVE_UP", attempts=attempt)
        return False

    def disconnect(self) -> None:
        if self.connector is not None:
            try:
                self.connector.close()
            except Exception:
                pass
        self.state = "DISCONNECTED"

    def on_disconnect(self) -> bool:
        """Connection dropped: reconnect with bounded backoff. Caller MUST then run REST reconciliation."""
        self.reconnect_count += 1
        self.state = "DISCONNECTED"
        self._emit("DISCONNECTED")
        return self.connect()

    def pump(self) -> int:
        """Poll connector once and dispatch normalized events. Returns number of events handled."""
        if self.state != "CONNECTED":
            return 0
        n = 0
        for raw in self.connector.poll():
            for ev in self.adapter.normalize_private_event(raw):
                self.last_event_ns = self._clock_ns()
                self.handler(ev)
                n += 1
        return n

    def health(self) -> Dict[str, Any]:
        return {"venue": self.adapter.venue, "state": self.state, "reconnect_count": self.reconnect_count,
                "consecutive_failures": self.consecutive_failures, "last_event_ns": self.last_event_ns,
                "last_error": self.last_error,
                "authoritative_recovery": "REST_RECONCILIATION"}
