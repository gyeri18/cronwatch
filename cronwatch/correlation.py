"""Alert correlation: group related alerts into correlated incidents."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatch.alerter import Alert


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class Incident:
    """A group of correlated alerts that form a single incident."""
    incident_id: str
    job_name: str
    kind: str
    alerts: List[Alert] = field(default_factory=list)
    opened_at: datetime = field(default_factory=_utcnow)
    closed_at: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    @property
    def size(self) -> int:
        return len(self.alerts)

    def add(self, alert: Alert) -> None:
        self.alerts.append(alert)

    def close(self, ts: Optional[datetime] = None) -> None:
        self.closed_at = ts or _utcnow()

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "job_name": self.job_name,
            "kind": self.kind,
            "size": self.size,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "is_open": self.is_open,
        }


class CorrelationEngine:
    """Correlates incoming alerts into incidents based on job+kind proximity."""

    def __init__(self, window: timedelta = timedelta(minutes=5),
                 clock=None) -> None:
        if window.total_seconds() <= 0:
            raise ValueError("window must be positive")
        self._window = window
        self._clock = clock or _utcnow
        self._open: Dict[str, Incident] = {}  # key -> Incident

    def _key(self, alert: Alert) -> str:
        return f"{alert.job_name}:{alert.kind}"

    def _is_expired(self, incident: Incident) -> bool:
        return (self._clock() - incident.opened_at) > self._window

    def ingest(self, alert: Alert) -> Incident:
        """Add alert to an existing open incident or open a new one."""
        key = self._key(alert)
        existing = self._open.get(key)
        if existing and not self._is_expired(existing):
            existing.add(alert)
            return existing
        # open new incident (close old expired one implicitly)
        incident = Incident(
            incident_id=str(uuid.uuid4()),
            job_name=alert.job_name,
            kind=alert.kind,
        )
        incident.add(alert)
        self._open[key] = incident
        return incident

    def close_incident(self, job_name: str, kind: str) -> Optional[Incident]:
        """Explicitly close an open incident for the given job+kind."""
        key = f"{job_name}:{kind}"
        incident = self._open.pop(key, None)
        if incident:
            incident.close(self._clock())
        return incident

    def open_incidents(self) -> List[Incident]:
        return [i for i in self._open.values() if i.is_open]
