"""Silence windows: suppress alerts during scheduled maintenance periods."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SilenceWindow:
    """A named time range during which alerts are suppressed."""

    name: str
    start: datetime  # timezone-aware
    end: datetime    # timezone-aware
    jobs: List[str] = field(default_factory=list)  # empty = all jobs

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if the window covers *at* (default: now)."""
        now = at if at is not None else _utcnow()
        return self.start <= now <= self.end

    def covers_job(self, job_name: str) -> bool:
        """Return True if this window applies to *job_name*."""
        return not self.jobs or job_name in self.jobs


class SilenceManager:
    """Registry of silence windows; answers whether a job is currently silenced."""

    def __init__(self) -> None:
        self._windows: List[SilenceWindow] = []

    def add(self, window: SilenceWindow) -> None:
        """Register a silence window."""
        self._windows.append(window)

    def remove(self, name: str) -> bool:
        """Remove a window by name.  Returns True if found and removed."""
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.name != name]
        return len(self._windows) < before

    def is_silenced(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Return True if *job_name* is covered by any active window."""
        return any(
            w.is_active(at) and w.covers_job(job_name)
            for w in self._windows
        )

    def active_windows(self, at: Optional[datetime] = None) -> List[SilenceWindow]:
        """Return all currently active windows."""
        return [w for w in self._windows if w.is_active(at)]

    def __len__(self) -> int:
        return len(self._windows)
