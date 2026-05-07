"""AuditedAlerter: wraps an Alerter and records every dispatched alert."""

from __future__ import annotations

from typing import Callable, List

from cronwatch.alerter import Alert, Alerter
from cronwatch.audit import AuditLog


class AuditedAlerter:
    """Decorator around Alerter that writes every alert to an AuditLog."""

    def __init__(self, alerter: Alerter, audit_log: AuditLog) -> None:
        self._alerter = alerter
        self._audit_log = audit_log

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Delegate handler registration to the wrapped alerter."""
        self._alerter.add_handler(handler)

    def send(self, alert: Alert) -> None:
        """Record the alert in the audit log, then dispatch it."""
        self._audit_log.record(alert)
        self._alerter.send(alert)

    @property
    def audit_log(self) -> AuditLog:
        return self._audit_log
