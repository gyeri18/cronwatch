"""Generates summary reports from job history."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from cronwatch.history import HistoryEntry, JobHistory


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    success_count: int
    failure_count: int
    missed_count: int
    slow_count: int
    avg_duration: Optional[float]
    max_duration: Optional[float]

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.success_count / self.total_runs


class Reporter:
    """Builds human-readable and structured reports from JobHistory."""

    def __init__(self, history: JobHistory) -> None:
        self._history = history

    def summarize(self, job_name: str) -> JobSummary:
        entries = self._history.get_job(job_name)
        counts: Dict[str, int] = defaultdict(int)
        durations: List[float] = []

        for e in entries:
            counts[e.status] += 1
            if e.duration_seconds is not None:
                durations.append(e.duration_seconds)

        avg = sum(durations) / len(durations) if durations else None
        mx = max(durations) if durations else None

        return JobSummary(
            job_name=job_name,
            total_runs=len(entries),
            success_count=counts["success"],
            failure_count=counts["failure"],
            missed_count=counts["missed"],
            slow_count=counts["slow"],
            avg_duration=avg,
            max_duration=mx,
        )

    def format_summary(self, summary: JobSummary) -> str:
        lines = [
            f"Job: {summary.job_name}",
            f"  Runs      : {summary.total_runs}",
            f"  Success   : {summary.success_count} ({summary.success_rate:.0%})",
            f"  Failures  : {summary.failure_count}",
            f"  Missed    : {summary.missed_count}",
            f"  Slow      : {summary.slow_count}",
        ]
        if summary.avg_duration is not None:
            lines.append(f"  Avg dur   : {summary.avg_duration:.2f}s")
        if summary.max_duration is not None:
            lines.append(f"  Max dur   : {summary.max_duration:.2f}s")
        return "\n".join(lines)

    def all_summaries(self) -> List[JobSummary]:
        names = {e.job_name for e in self._history.get_recent(limit=len(self._history))}
        return [self.summarize(n) for n in sorted(names)]
