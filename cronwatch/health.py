"""Health check endpoint and status reporter for cronwatch daemon."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cronwatch.daemon import Daemon
    from cronwatch.metrics import JobMetrics


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HealthStatus:
    """Snapshot of daemon and job health at a point in time."""

    def __init__(
        self,
        running: bool,
        uptime_seconds: float | None,
        job_statuses: dict[str, dict[str, Any]],
        checked_at: datetime | None = None,
    ) -> None:
        self.running = running
        self.uptime_seconds = uptime_seconds
        self.job_statuses = job_statuses
        self.checked_at = checked_at or _utcnow()

    @property
    def healthy(self) -> bool:
        """True when daemon is running and no job has a zero success rate."""
        if not self.running:
            return False
        for status in self.job_statuses.values():
            if status.get("total_runs", 0) > 0 and status.get("success_rate", 1.0) == 0.0:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "running": self.running,
            "uptime_seconds": self.uptime_seconds,
            "checked_at": self.checked_at.isoformat(),
            "jobs": self.job_statuses,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class HealthChecker:
    """Builds a HealthStatus from a live Daemon and its job metrics."""

    def __init__(self, daemon: "Daemon", metrics: dict[str, "JobMetrics"]) -> None:
        self._daemon = daemon
        self._metrics = metrics

    def check(self) -> HealthStatus:
        job_statuses: dict[str, dict[str, Any]] = {}
        for job_name, m in self._metrics.items():
            job_statuses[job_name] = {
                "total_runs": m.total_runs,
                "slow_runs": m.slow_runs,
                "missed_runs": m.missed_runs,
                "success_rate": round(m.success_rate, 4),
                "avg_duration_seconds": round(m.avg_duration, 4) if m.avg_duration is not None else None,
                "max_duration_seconds": round(m.max_duration, 4) if m.max_duration is not None else None,
            }
        return HealthStatus(
            running=self._daemon.running,
            uptime_seconds=self._daemon.uptime_seconds,
            job_statuses=job_statuses,
        )
