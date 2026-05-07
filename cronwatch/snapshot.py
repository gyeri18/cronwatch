"""Point-in-time snapshot of watcher state for diagnostics and reporting."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobSnapshot:
    """Immutable view of a single watched job at snapshot time."""

    name: str
    schedule: str
    last_start: Optional[datetime]
    last_finish: Optional[datetime]
    last_exit_code: Optional[int]
    is_running: bool
    total_runs: int
    missed_count: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "schedule": self.schedule,
            "last_start": self.last_start.isoformat() if self.last_start else None,
            "last_finish": self.last_finish.isoformat() if self.last_finish else None,
            "last_exit_code": self.last_exit_code,
            "is_running": self.is_running,
            "total_runs": self.total_runs,
            "missed_count": self.missed_count,
        }


@dataclass
class WatcherSnapshot:
    """Immutable view of all watched jobs captured at a single moment."""

    captured_at: datetime = field(default_factory=_utcnow)
    jobs: List[JobSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at.isoformat(),
            "jobs": [j.to_dict() for j in self.jobs],
        }

    def job(self, name: str) -> Optional[JobSnapshot]:
        """Return the snapshot for a specific job, or None."""
        for j in self.jobs:
            if j.name == name:
                return j
        return None


class SnapshotCollector:
    """Builds WatcherSnapshot objects from the live Watcher state."""

    def __init__(self, watcher) -> None:
        self._watcher = watcher

    def collect(self) -> WatcherSnapshot:
        """Capture current state of all registered jobs."""
        jobs: List[JobSnapshot] = []
        for watched in self._watcher.jobs.values():
            tracker = self._watcher.tracker
            runs = tracker.runs(watched.config.name)
            last_run = runs[-1] if runs else None
            jobs.append(
                JobSnapshot(
                    name=watched.config.name,
                    schedule=watched.config.schedule,
                    last_start=last_run.started_at if last_run else None,
                    last_finish=last_run.finished_at if last_run else None,
                    last_exit_code=last_run.exit_code if last_run else None,
                    is_running=last_run.is_running() if last_run else False,
                    total_runs=len(runs),
                    missed_count=tracker.missed_count(watched.config.name),
                )
            )
        return WatcherSnapshot(jobs=jobs)
