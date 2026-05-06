"""Persistent run history storage for cron jobs."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class HistoryEntry:
    job_name: str
    started_at: str
    finished_at: Optional[str]
    duration_seconds: Optional[float]
    exit_code: Optional[int]
    status: str  # 'success', 'failure', 'missed', 'slow'

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


class JobHistory:
    """Stores and retrieves job run history from a JSON file."""

    def __init__(self, path: str, max_entries: int = 500) -> None:
        self._path = Path(path)
        self._max_entries = max_entries
        self._entries: List[HistoryEntry] = []
        if self._path.exists():
            self._load()

    def _load(self) -> None:
        with open(self._path, "r") as fh:
            raw = json.load(fh)
        self._entries = [HistoryEntry.from_dict(r) for r in raw]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as fh:
            json.dump([e.to_dict() for e in self._entries], fh, indent=2)

    def record(self, entry: HistoryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._save()

    def get_job(self, job_name: str) -> List[HistoryEntry]:
        return [e for e in self._entries if e.job_name == job_name]

    def get_recent(self, limit: int = 50) -> List[HistoryEntry]:
        return self._entries[-limit:]

    def clear(self) -> None:
        self._entries = []
        self._save()

    def __len__(self) -> int:
        return len(self._entries)
