"""Alert dispatching with optional throttling support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.throttle import AlertThrottle


@dataclass
class Alert:
    kind: str          # e.g. "missed", "slow", "recovered"
    job_name: str
    message: str

    def __str__(self) -> str:
        return f"[{self.kind.upper()}] {self.job_name}: {self.message}"


Handler = Callable[[Alert], None]


class Alerter:
    """Dispatches alerts to registered handlers.

    Optionally wraps dispatch with an :class:`AlertThrottle` so that
    repeated alerts for the same (kind, job) pair are suppressed until
    the configured cool-down period has elapsed.
    """

    def __init__(
        self,
        throttle: Optional[AlertThrottle] = None,
    ) -> None:
        self._handlers: List[Handler] = []
        self._throttle = throttle
        self.sent_count: int = 0
        self.suppressed_count: int = 0

    def add_handler(self, handler: Handler) -> None:
        """Register a callable that receives :class:`Alert` objects."""
        self._handlers.append(handler)

    def send(self, alert: Alert) -> bool:
        """Dispatch *alert* to all handlers.

        Returns True if the alert was dispatched, False if throttled.
        """
        if self._throttle is not None:
            if not self._throttle.allow(alert.kind, alert.job_name):
                self.suppressed_count += 1
                return False

        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:  # noqa: BLE001
                pass

        self.sent_count += 1
        return True

    def alert_missed(self, job_name: str, message: str = "Job did not run") -> bool:
        return self.send(Alert(kind="missed", job_name=job_name, message=message))

    def alert_slow(self, job_name: str, message: str = "Job exceeded time limit") -> bool:
        return self.send(Alert(kind="slow", job_name=job_name, message=message))

    def alert_recovered(self, job_name: str, message: str = "Job is running again") -> bool:
        return self.send(Alert(kind="recovered", job_name=job_name, message=message))

    @property
    def handler_count(self) -> int:
        return len(self._handlers)
