"""Alert escalation policy: re-alert after repeated failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EscalationPolicy:
    """Defines when to escalate repeated alerts for a job."""

    # Escalate after this many consecutive failures
    threshold: int = 3
    # Re-alert every N failures after threshold is reached
    repeat_every: int = 1
    # Optional: only escalate if failures span at least this many seconds
    min_window_seconds: Optional[float] = None

    def should_escalate(self, state: "EscalationState") -> bool:
        count = state.consecutive_failures
        if count < self.threshold:
            return False
        if self.min_window_seconds is not None and state.window_seconds() < self.min_window_seconds:
            return False
        excess = count - self.threshold
        return excess % self.repeat_every == 0


@dataclass
class EscalationState:
    """Tracks consecutive failure counts per job."""

    job_name: str
    consecutive_failures: int = 0
    first_failure_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    escalation_count: int = 0
    _extra: dict = field(default_factory=dict)

    def record_failure(self, when: Optional[datetime] = None) -> None:
        now = when or _utcnow()
        if self.consecutive_failures == 0:
            self.first_failure_at = now
        self.last_failure_at = now
        self.consecutive_failures += 1

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.first_failure_at = None
        self.last_failure_at = None
        self.escalation_count = 0

    def mark_escalated(self) -> None:
        self.escalation_count += 1

    def window_seconds(self) -> float:
        if self.first_failure_at is None or self.last_failure_at is None:
            return 0.0
        return (self.last_failure_at - self.first_failure_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "consecutive_failures": self.consecutive_failures,
            "escalation_count": self.escalation_count,
            "first_failure_at": self.first_failure_at.isoformat() if self.first_failure_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
        }
