"""Alert data-class and dispatcher with optional retry support."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.retry import RetryPolicy, with_retry

log = logging.getLogger(__name__)

Handler = Callable[["Alert"], None]


@dataclass
class Alert:
    """A single alert event."""

    kind: str          # e.g. "missed", "slow", "error"
    job_name: str
    message: str
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.kind.upper()}] {self.job_name}: {self.message}"


class Alerter:
    """Dispatches :class:`Alert` objects to registered handlers.

    Each handler is called with the alert.  If *retry_policy* is provided,
    failed handler calls are retried according to that policy.
    """

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self._handlers: List[Handler] = []
        self._retry_policy = retry_policy or RetryPolicy(max_attempts=1)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_handler(self, handler: Handler) -> None:
        """Register *handler* to receive future alerts."""
        self._handlers.append(handler)

    def remove_handler(self, handler: Handler) -> None:
        """Unregister *handler* (no-op if not present)."""
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> None:
        """Deliver *alert* to every registered handler."""
        for handler in list(self._handlers):
            self._deliver(handler, alert)

    def _deliver(self, handler: Handler, alert: Alert) -> None:
        policy = self._retry_policy

        def attempt() -> None:
            handler(alert)

        state = with_retry(attempt, policy)
        if not state.succeeded:
            log.error(
                "Handler %r failed after %d attempt(s): %s",
                handler,
                state.attempts,
                state.last_error,
            )

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    def missed(self, job_name: str, message: str, **extra) -> None:
        self.send(Alert(kind="missed", job_name=job_name, message=message, extra=extra))

    def slow(self, job_name: str, message: str, **extra) -> None:
        self.send(Alert(kind="slow", job_name=job_name, message=message, extra=extra))

    def error(self, job_name: str, message: str, **extra) -> None:
        self.send(Alert(kind="error", job_name=job_name, message=message, extra=extra))
