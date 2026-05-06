"""Tracker: records job run start/finish times and exposes run history."""

from datetime import datetime, timezone
from typing import Dict, List, Optional


class JobRun:
    """Represents a single execution of a cron job."""

    def __init__(self, run_id: str, started_at: datetime) -> None:
        self.run_id = run_id
        self.started_at = started_at
        self.finished_at: Optional[datetime] = None

    @property
    def duration(self) -> Optional[float]:
        """Return elapsed seconds, or None if still running."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        return self.finished_at is None


class JobTracker:
    """Tracks multiple runs for a single job."""

    def __init__(self) -> None:
        self._runs: Dict[str, JobRun] = {}
        self._order: List[str] = []

    def record_start(self, run_id: str, at: Optional[datetime] = None) -> JobRun:
        ts = at or datetime.now(timezone.utc)
        run = JobRun(run_id, ts)
        self._runs[run_id] = run
        self._order.append(run_id)
        return run

    def record_finish(self, run_id: str, at: Optional[datetime] = None) -> Optional[JobRun]:
        run = self._runs.get(run_id)
        if run is None:
            return None
        run.finished_at = at or datetime.now(timezone.utc)
        return run

    def get_run(self, run_id: str) -> Optional[JobRun]:
        return self._runs.get(run_id)

    def all_runs(self) -> List[JobRun]:
        return [self._runs[rid] for rid in self._order]

    def last_start_time(self) -> Optional[datetime]:
        if not self._order:
            return None
        return self._runs[self._order[-1]].started_at

    def has_run_started_after(self, ts: datetime) -> bool:
        """Return True if any run started at or after *ts*."""
        return any(r.started_at >= ts for r in self._runs.values())
