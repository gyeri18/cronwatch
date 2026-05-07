"""Alerter wrapper that correlates alerts into incidents before forwarding."""
from __future__ import annotations

from datetime import timedelta
from typing import Callable, List, Optional

from cronwatch.alerter import Alert, Alerter
from cronwatch.correlation import CorrelationEngine, Incident


IncidentCallback = Callable[[Incident, Alert], None]


class CorrelatedAlerter:
    """Wraps an Alerter and groups alerts into incidents.

    The underlying alerter is only called when a *new* incident is opened.
    Subsequent correlated alerts are silently tracked inside the incident.
    An optional ``on_update`` callback fires for every ingested alert.
    """

    def __init__(
        self,
        alerter: Alerter,
        window: timedelta = timedelta(minutes=5),
        on_update: Optional[IncidentCallback] = None,
        clock=None,
    ) -> None:
        self._alerter = alerter
        self._engine = CorrelationEngine(window=window, clock=clock)
        self._on_update = on_update
        self._new_ids: set = set()

    def send(self, alert: Alert) -> Incident:
        """Ingest *alert*, forward to wrapped alerter only if a new incident
        is opened.  Returns the correlated Incident."""
        incident = self._engine.ingest(alert)
        is_new = incident.incident_id not in self._new_ids
        if is_new:
            self._new_ids.add(incident.incident_id)
            self._alerter.send(alert)
        if self._on_update:
            self._on_update(incident, alert)
        return incident

    def close_incident(self, job_name: str, kind: str) -> Optional[Incident]:
        """Close an open incident and remove it from tracking."""
        incident = self._engine.close_incident(job_name, kind)
        if incident:
            self._new_ids.discard(incident.incident_id)
        return incident

    def open_incidents(self) -> List[Incident]:
        """Return all currently open incidents."""
        return self._engine.open_incidents()

    def add_handler(self, handler) -> None:
        """Delegate handler registration to the wrapped alerter."""
        self._alerter.add_handler(handler)
