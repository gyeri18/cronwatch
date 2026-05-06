"""Alerter wrapper that skips notification when the circuit breaker is open."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from cronwatch.alerter import Alert
from cronwatch.circuit_breaker import CircuitBreaker

Handler = Callable[[Alert], None]


class CircuitBrokenAlerter:
    """Wraps a list of handlers with a per-handler circuit breaker.

    If a handler raises an exception it counts as a failure.  Once the
    circuit opens, that handler is skipped until the recovery timeout
    elapses and a probe succeeds.

    Args:
        failure_threshold: consecutive failures before opening.
        recovery_timeout: seconds before attempting recovery.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._handlers: List[Handler] = []
        self._breakers: Dict[int, CircuitBreaker] = {}

    def add_handler(self, handler: Handler) -> None:
        hid = id(handler)
        self._handlers.append(handler)
        self._breakers[hid] = CircuitBreaker(
            failure_threshold=self._failure_threshold,
            recovery_timeout=self._recovery_timeout,
            name=getattr(handler, "__name__", repr(handler)),
        )

    def send(self, alert: Alert) -> Dict[str, Any]:
        """Dispatch *alert* to all handlers, respecting circuit state.

        Returns a dict mapping handler name -> 'sent' | 'open' | 'error'.
        """
        results: Dict[str, Any] = {}
        for handler in self._handlers:
            breaker = self._breakers[id(handler)]
            label = breaker.name
            if not breaker.allow_request():
                results[label] = "open"
                continue
            try:
                handler(alert)
                breaker.record_success()
                results[label] = "sent"
            except Exception as exc:  # noqa: BLE001
                breaker.record_failure()
                results[label] = f"error: {exc}"
        return results

    def breaker_for(self, handler: Handler) -> CircuitBreaker:
        """Return the CircuitBreaker associated with *handler*."""
        return self._breakers[id(handler)]

    def reset_all(self) -> None:
        """Manually reset every circuit breaker to CLOSED."""
        for breaker in self._breakers.values():
            breaker.reset()
