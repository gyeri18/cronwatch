"""Watcher: ties together schedule, tracker, and alerter to monitor cron jobs."""

from datetime import datetime, timezone
from typing import Dict, Optional

from cronwatch.alerter import Alerter
from cronwatch.schedule import CronSchedule
from cronwatch.tracker import JobTracker


class WatchedJob:
    """Configuration and state for a single monitored cron job."""

    def __init__(
        self,
        name: str,
        expression: str,
        timeout_seconds: float = 3600.0,
        grace_seconds: float = 60.0,
    ) -> None:
        self.name = name
        self.schedule = CronSchedule(expression)
        self.timeout_seconds = timeout_seconds
        self.grace_seconds = grace_seconds


class Watcher:
    """Monitors registered cron jobs and fires alerts via an Alerter."""

    def __init__(self, alerter: Alerter) -> None:
        self._alerter = alerter
        self._jobs: Dict[str, WatchedJob] = {}
        self._trackers: Dict[str, JobTracker] = {}

    def register(self, job: WatchedJob) -> None:
        """Register a job for monitoring."""
        self._jobs[job.name] = job
        self._trackers[job.name] = JobTracker()

    def record_start(self, job_name: str, run_id: str, at: Optional[datetime] = None) -> None:
        """Record that a job has started."""
        ts = at or datetime.now(timezone.utc)
        self._trackers[job_name].record_start(run_id, ts)

    def record_finish(self, job_name: str, run_id: str, at: Optional[datetime] = None) -> None:
        """Record that a job has finished and check for slow runs."""
        ts = at or datetime.now(timezone.utc)
        self._trackers[job_name].record_finish(run_id, ts)
        run = self._trackers[job_name].get_run(run_id)
        job = self._jobs[job_name]
        if run and run.duration is not None and run.duration > job.timeout_seconds:
            self._alerter.send(
                kind="slow",
                job_name=job_name,
                detail=f"duration {run.duration:.1f}s exceeded timeout {job.timeout_seconds}s",
            )

    def check_missed(self, now: Optional[datetime] = None) -> None:
        """Check all jobs for missed runs since their last recorded start."""
        ts = now or datetime.now(timezone.utc)
        for name, job in self._jobs.items():
            tracker = self._trackers[name]
            last = tracker.last_start_time()
            expected = job.schedule.next_run(last) if last else None
            if expected is None:
                continue
            deadline = expected.timestamp() + job.grace_seconds
            if ts.timestamp() > deadline and not tracker.has_run_started_after(expected):
                self._alerter.send(
                    kind="missed",
                    job_name=name,
                    detail=f"expected at {expected.isoformat()}, grace {job.grace_seconds}s elapsed",
                )
