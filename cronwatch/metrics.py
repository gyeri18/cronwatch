"""Collects and exposes runtime metrics for monitored cron jobs."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JobMetrics:
    """Accumulated metrics for a single job."""

    name: str
    run_count: int = 0
    miss_count: int = 0
    slow_count: int = 0
    durations: List[float] = field(default_factory=list)

    @property
    def avg_duration(self) -> Optional[float]:
        """Mean duration across all completed runs, or None if no runs."""
        return statistics.mean(self.durations) if self.durations else None

    @property
    def max_duration(self) -> Optional[float]:
        """Maximum observed duration, or None if no runs."""
        return max(self.durations) if self.durations else None

    @property
    def success_rate(self) -> Optional[float]:
        """Fraction of runs that were neither missed nor slow (0.0–1.0)."""
        if self.run_count == 0:
            return None
        bad = self.miss_count + self.slow_count
        return max(0.0, (self.run_count - bad) / self.run_count)

    def record_run(self, duration: float, *, slow: bool = False) -> None:
        """Record a completed run."""
        self.run_count += 1
        self.durations.append(duration)
        if slow:
            self.slow_count += 1

    def record_miss(self) -> None:
        """Record a missed run (job did not start on time)."""
        self.miss_count += 1


class MetricsCollector:
    """Central registry of per-job metrics."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobMetrics] = {}

    def _get_or_create(self, job_name: str) -> JobMetrics:
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(name=job_name)
        return self._jobs[job_name]

    def record_run(self, job_name: str, duration: float, *, slow: bool = False) -> None:
        """Record a completed run for *job_name*."""
        self._get_or_create(job_name).record_run(duration, slow=slow)

    def record_miss(self, job_name: str) -> None:
        """Record a missed execution for *job_name*."""
        self._get_or_create(job_name).record_miss()

    def get(self, job_name: str) -> Optional[JobMetrics]:
        """Return metrics for *job_name*, or None if never seen."""
        return self._jobs.get(job_name)

    def all_metrics(self) -> Dict[str, JobMetrics]:
        """Return a shallow copy of the full metrics registry."""
        return dict(self._jobs)

    def summary(self) -> str:
        """Human-readable one-line summary per job."""
        if not self._jobs:
            return "No metrics recorded."
        lines = []
        for m in self._jobs.values():
            avg = f"{m.avg_duration:.2f}s" if m.avg_duration is not None else "n/a"
            sr = f"{m.success_rate * 100:.1f}%" if m.success_rate is not None else "n/a"
            lines.append(
                f"{m.name}: runs={m.run_count} misses={m.miss_count} "
                f"slow={m.slow_count} avg={avg} success={sr}"
            )
        return "\n".join(lines)
