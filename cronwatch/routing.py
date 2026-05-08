"""Alert routing: send alerts to different handlers based on job name or alert kind."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Callable, List, Optional

from cronwatch.alerter import Alert

Handler = Callable[[Alert], None]


@dataclass
class RoutingRule:
    """A single routing rule that maps a pattern to a handler."""

    handler: Handler
    job_pattern: Optional[str] = None   # fnmatch pattern, None = match all
    kind_filter: Optional[str] = None   # exact kind, None = match all

    def matches(self, alert: Alert) -> bool:
        if self.job_pattern is not None:
            if not fnmatch(alert.job, self.job_pattern):
                return False
        if self.kind_filter is not None:
            if alert.kind != self.kind_filter:
                return False
        return True


@dataclass
class AlertRouter:
    """Routes alerts to one or more handlers according to registered rules.

    Rules are evaluated in insertion order; all matching rules fire
    (fan-out), unless *first_match_only* is True.
    """

    first_match_only: bool = False
    _rules: List[RoutingRule] = field(default_factory=list, init=False, repr=False)

    def add_rule(
        self,
        handler: Handler,
        *,
        job_pattern: Optional[str] = None,
        kind_filter: Optional[str] = None,
    ) -> None:
        """Register a routing rule."""
        self._rules.append(
            RoutingRule(handler=handler, job_pattern=job_pattern, kind_filter=kind_filter)
        )

    def route(self, alert: Alert) -> int:
        """Dispatch *alert* to matching handlers.

        Returns the number of handlers that received the alert.
        """
        dispatched = 0
        for rule in self._rules:
            if rule.matches(alert):
                rule.handler(alert)
                dispatched += 1
                if self.first_match_only:
                    break
        return dispatched

    @property
    def rules(self) -> List[RoutingRule]:
        return list(self._rules)
