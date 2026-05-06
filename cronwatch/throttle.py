"""Alert throttling to prevent notification storms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ThrottleRule:
    """Defines how often a specific alert kind may fire for a job."""

    kind: str
    job_name: str
    min_interval_seconds: float


@dataclass
class ThrottleState:
    """Tracks when an alert was last sent."""

    last_sent: Optional[datetime] = None
    suppressed_count: int = 0

    def should_send(self, now: datetime, min_interval_seconds: float) -> bool:
        if self.last_sent is None:
            return True
        elapsed = (now - self.last_sent).total_seconds()
        return elapsed >= min_interval_seconds

    def record_sent(self, now: datetime) -> None:
        self.last_sent = now
        self.suppressed_count = 0

    def record_suppressed(self) -> None:
        self.suppressed_count += 1


class AlertThrottle:
    """Manages per-job, per-kind alert throttling."""

    def __init__(self, default_interval_seconds: float = 300.0) -> None:
        self.default_interval_seconds = default_interval_seconds
        self._rules: Dict[Tuple[str, str], float] = {}
        self._states: Dict[Tuple[str, str], ThrottleState] = {}

    def set_rule(self, kind: str, job_name: str, min_interval_seconds: float) -> None:
        """Register a throttle rule for a specific (kind, job) pair."""
        self._rules[(kind, job_name)] = min_interval_seconds

    def _get_interval(self, kind: str, job_name: str) -> float:
        return self._rules.get((kind, job_name), self.default_interval_seconds)

    def _get_state(self, kind: str, job_name: str) -> ThrottleState:
        key = (kind, job_name)
        if key not in self._states:
            self._states[key] = ThrottleState()
        return self._states[key]

    def allow(self, kind: str, job_name: str) -> bool:
        """Return True if the alert should be sent, False if throttled."""
        now = _utcnow()
        interval = self._get_interval(kind, job_name)
        state = self._get_state(kind, job_name)
        if state.should_send(now, interval):
            state.record_sent(now)
            return True
        state.record_suppressed()
        return False

    def suppressed_count(self, kind: str, job_name: str) -> int:
        """Return how many alerts were suppressed since the last sent alert."""
        return self._get_state(kind, job_name).suppressed_count

    def reset(self, kind: str, job_name: str) -> None:
        """Clear throttle state for a (kind, job) pair."""
        self._states.pop((kind, job_name), None)
