"""Alerter wrapper that dispatches through an AlertRouter."""
from __future__ import annotations

from typing import Callable, Optional

from cronwatch.alerter import Alert
from cronwatch.routing import AlertRouter

Handler = Callable[[Alert], None]


class RoutedAlerter:
    """An alerter that sends each alert through an :class:`AlertRouter`.

    Handlers are registered on the router with optional *job_pattern* and
    *kind_filter* constraints, giving fine-grained control over which
    handler receives which alert.

    Example::

        ra = RoutedAlerter()
        ra.add_handler(ops_pager, kind_filter="missed")
        ra.add_handler(slack_hook, job_pattern="billing-*")
        ra.send(alert)
    """

    def __init__(self, first_match_only: bool = False) -> None:
        self._router = AlertRouter(first_match_only=first_match_only)

    def add_handler(
        self,
        handler: Handler,
        *,
        job_pattern: Optional[str] = None,
        kind_filter: Optional[str] = None,
    ) -> None:
        """Add *handler* to the router with optional match constraints."""
        self._router.add_rule(
            handler, job_pattern=job_pattern, kind_filter=kind_filter
        )

    def send(self, alert: Alert) -> int:
        """Route *alert* and return the number of handlers invoked."""
        return self._router.route(alert)

    @property
    def router(self) -> AlertRouter:
        return self._router
