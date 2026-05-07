"""Audit log: records every alert dispatched with timestamp and metadata."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cronwatch.alerter import Alert


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEntry:
    timestamp: datetime
    job: str
    kind: str
    message: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "job": self.job,
            "kind": self.kind,
            "message": self.message,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            job=data["job"],
            kind=data["kind"],
            message=data["message"],
            extra=data.get("extra", {}),
        )


class AuditLog:
    """Thread-safe in-memory audit log with optional file persistence."""

    def __init__(self, path: Optional[Path] = None, max_entries: int = 1000) -> None:
        self._path = path
        self._max_entries = max_entries
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        if path and path.exists():
            self._load()

    def record(self, alert: Alert, *, clock=_utcnow) -> AuditEntry:
        entry = AuditEntry(
            timestamp=clock(),
            job=alert.job,
            kind=alert.kind,
            message=alert.message,
            extra=dict(alert.extra),
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]
            if self._path:
                self._append_to_file(entry)
        return entry

    def entries(self, job: Optional[str] = None) -> List[AuditEntry]:
        with self._lock:
            if job is None:
                return list(self._entries)
            return [e for e in self._entries if e.job == job]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _append_to_file(self, entry: AuditEntry) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def _load(self) -> None:
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    self._entries.append(AuditEntry.from_dict(json.loads(line)))
