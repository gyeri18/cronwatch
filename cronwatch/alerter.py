"""Alert system for missed or slow cron job runs."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional


@dataclass
class Alert:
    job_name: str
    kind: str  # 'missed' | 'slow' | 'failed'
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return (
            f"[{self.triggered_at.isoformat()}] "
            f"{self.kind.upper()} — {self.job_name}: {self.message}"
        )


class Alerter:
    """Evaluates job run data and fires alerts via registered handlers."""

    def __init__(
        self,
        slow_threshold: timedelta = timedelta(minutes=5),
        handlers: Optional[List[Callable[[Alert], None]]] = None,
    ) -> None:
        self.slow_threshold = slow_threshold
        self._handlers: List[Callable[[Alert], None]] = handlers or []
        self.history: List[Alert] = []

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a callable that receives Alert objects."""
        self._handlers.append(handler)

    def _fire(self, alert: Alert) -> None:
        self.history.append(alert)
        for handler in self._handlers:
            handler(alert)

    def check_missed(
        self, job_name: str, expected_at: datetime, grace: timedelta = timedelta(minutes=1)
    ) -> bool:
        """Fire a 'missed' alert if now is past expected_at + grace."""
        deadline = expected_at + grace
        if datetime.utcnow() > deadline:
            self._fire(
                Alert(
                    job_name=job_name,
                    kind="missed",
                    message=(
                        f"Expected at {expected_at.isoformat()}, "
                        f"grace period ({grace}) exceeded."
                    ),
                )
            )
            return True
        return False

    def check_slow(self, job_name: str, duration: timedelta) -> bool:
        """Fire a 'slow' alert if duration exceeds the configured threshold."""
        if duration > self.slow_threshold:
            self._fire(
                Alert(
                    job_name=job_name,
                    kind="slow",
                    message=(
                        f"Ran for {duration}, threshold is {self.slow_threshold}."
                    ),
                )
            )
            return True
        return False

    def check_failed(self, job_name: str, exit_code: int) -> bool:
        """Fire a 'failed' alert for non-zero exit codes."""
        if exit_code != 0:
            self._fire(
                Alert(
                    job_name=job_name,
                    kind="failed",
                    message=f"Exited with code {exit_code}.",
                )
            )
            return True
        return False
