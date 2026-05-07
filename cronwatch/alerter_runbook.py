"""Alerter decorator that injects runbook annotations into alerts before dispatch."""
from __future__ import annotations

from typing import Callable, List

from cronwatch.alerter import Alert, Alerter
from cronwatch.runbook import RunbookRegistry


class RunbookAlerter:
    """Wraps an Alerter, enriching each alert's extra dict with runbook data."""

    def __init__(self, alerter: Alerter, registry: RunbookRegistry) -> None:
        self._alerter = alerter
        self._registry = registry

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Delegate handler registration to the underlying alerter."""
        self._alerter.add_handler(handler)

    def send(self, alert: Alert) -> None:
        """Annotate alert with runbook info then forward to the underlying alerter."""
        enriched_extra = self._registry.annotate(
            alert.kind, alert.job, alert.extra
        )
        enriched = Alert(
            kind=alert.kind,
            job=alert.job,
            message=alert.message,
            extra=enriched_extra,
        )
        self._alerter.send(enriched)

    @property
    def registry(self) -> RunbookRegistry:
        """Expose the underlying registry for inspection."""
        return self._registry

    @property
    def handlers(self) -> List[Callable[[Alert], None]]:
        """Expose the underlying alerter's handlers."""
        return self._alerter.handlers
