"""Integrates JobHistory recording into the Watcher event flow."""

from datetime import datetime, timezone
from typing import Optional

from cronwatch.history import HistoryEntry, JobHistory
from cronwatch.tracker import JobRun


class HistoryRecorder:
    """Attaches to Watcher events and persists runs to JobHistory."""

    def __init__(self, history: JobHistory) -> None:
        self._history = history

    def _iso(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.astimezone(timezone.utc).isoformat()

    def record_run(
        self,
        run: JobRun,
        status: str,
        exit_code: Optional[int] = None,
    ) -> HistoryEntry:
        entry = HistoryEntry(
            job_name=run.job_name,
            started_at=self._iso(run.started_at),
            finished_at=self._iso(run.finished_at),
            duration_seconds=run.duration,
            exit_code=exit_code,
            status=status,
        )
        self._history.record(entry)
        return entry

    def record_missed(self, job_name: str, expected_at: datetime) -> HistoryEntry:
        ts = self._iso(expected_at)
        entry = HistoryEntry(
            job_name=job_name,
            started_at=ts,
            finished_at=None,
            duration_seconds=None,
            exit_code=None,
            status="missed",
        )
        self._history.record(entry)
        return entry

    def status_for_run(
        self,
        run: JobRun,
        slow_threshold: Optional[float] = None,
        exit_code: Optional[int] = None,
    ) -> str:
        if exit_code is not None and exit_code != 0:
            return "failure"
        if slow_threshold is not None and run.duration is not None:
            if run.duration > slow_threshold:
                return "slow"
        return "success"
