"""Tracks cron job execution state and detects missed or slow runs."""

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.schedule import CronSchedule


@dataclass
class JobRun:
    """Records a single execution of a cron job."""
    started_at: float
    finished_at: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at

    @property
    def is_running(self) -> bool:
        return self.finished_at is None


@dataclass
class JobTracker:
    """Tracks execution state for a single named cron job."""
    name: str
    schedule: CronSchedule
    timeout_seconds: float = 300.0
    history: list = field(default_factory=list)
    _current_run: Optional[JobRun] = field(default=None, repr=False)

    def record_start(self, timestamp: Optional[float] = None) -> JobRun:
        """Record that the job has started."""
        ts = timestamp if timestamp is not None else time.time()
        run = JobRun(started_at=ts)
        self._current_run = run
        self.history.append(run)
        return run

    def record_finish(self, timestamp: Optional[float] = None) -> Optional[JobRun]:
        """Record that the current job run has finished."""
        if self._current_run is None:
            return None
        ts = timestamp if timestamp is not None else time.time()
        self._current_run.finished_at = ts
        run = self._current_run
        self._current_run = None
        return run

    def is_missed(self, reference_time: Optional[float] = None) -> bool:
        """Return True if a scheduled run appears to have been missed."""
        now = reference_time if reference_time is not None else time.time()
        expected = self.schedule.next_run(before=now)
        if expected is None:
            return False
        if not self.history:
            return True
        last_start = self.history[-1].started_at
        return last_start < expected

    def is_slow(self) -> bool:
        """Return True if the current run has exceeded the timeout threshold."""
        if self._current_run is None:
            return False
        elapsed = time.time() - self._current_run.started_at
        return elapsed > self.timeout_seconds

    @property
    def last_run(self) -> Optional[JobRun]:
        return self.history[-1] if self.history else None
