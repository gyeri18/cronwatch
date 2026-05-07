"""Runbook registry: attach remediation notes and links to alert kinds."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RunbookEntry:
    """A single runbook entry associated with an alert kind and optional job."""

    kind: str
    title: str
    steps: List[str] = field(default_factory=list)
    url: Optional[str] = None
    job: Optional[str] = None  # None means applies to all jobs

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "steps": list(self.steps),
            "url": self.url,
            "job": self.job,
        }


class RunbookRegistry:
    """Stores and retrieves runbook entries keyed by (kind, job)."""

    def __init__(self) -> None:
        self._entries: List[RunbookEntry] = []

    def register(self, entry: RunbookEntry) -> None:
        """Add a runbook entry to the registry."""
        self._entries.append(entry)

    def lookup(
        self, kind: str, job: Optional[str] = None
    ) -> Optional[RunbookEntry]:
        """Return the most-specific matching entry (job-specific beats wildcard)."""
        job_specific: Optional[RunbookEntry] = None
        wildcard: Optional[RunbookEntry] = None

        for entry in self._entries:
            if entry.kind != kind:
                continue
            if entry.job == job:
                job_specific = entry
            elif entry.job is None:
                wildcard = entry

        return job_specific if job_specific is not None else wildcard

    def all_for_kind(self, kind: str) -> List[RunbookEntry]:
        """Return all entries matching the given kind."""
        return [e for e in self._entries if e.kind == kind]

    def annotate(self, kind: str, job: Optional[str], extra: Dict) -> Dict:
        """Merge runbook info into an alert extra dict (non-destructive)."""
        entry = self.lookup(kind, job)
        if entry is None:
            return extra
        result = dict(extra)
        result.setdefault("runbook_title", entry.title)
        if entry.url:
            result.setdefault("runbook_url", entry.url)
        if entry.steps:
            result.setdefault("runbook_steps", entry.steps)
        return result
