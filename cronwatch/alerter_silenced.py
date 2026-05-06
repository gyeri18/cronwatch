"""Alerter decorator that suppresses notifications during silence windows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from cronwatch.alerter import Alert, Alerter
from cronwatch.silence import SilenceManager


class SilencedAlerter:
    """Wraps an :class:`Alerter` and skips alerts covered by a
    :class:`SilenceManager`.

    Parameters
    ----------
    alerter:
        Underlying alerter that actually dispatches notifications.
    silence_manager:
        Registry of active silence windows.
    on_suppressed:
        Optional callback invoked with the suppressed :class:`Alert` so
        callers can log or count suppressions.
    """

    def __init__(
        self,
        alerter: Alerter,
        silence_manager: SilenceManager,
        on_suppressed: Optional[Callable[[Alert], None]] = None,
    ) -> None:
        self._alerter = alerter
        self._silence = silence_manager
        self._on_suppressed = on_suppressed
        self.suppressed_count: int = 0

    def send(self, alert: Alert, at: Optional[datetime] = None) -> bool:
        """Send *alert* unless a silence window covers the job.

        Returns
        -------
        bool
            ``True`` if the alert was forwarded, ``False`` if suppressed.
        """
        now = at if at is not None else datetime.now(timezone.utc)
        if self._silence.is_silenced(alert.job_name, at=now):
            self.suppressed_count += 1
            if self._on_suppressed is not None:
                self._on_suppressed(alert)
            return False
        self._alerter.send(alert)
        return True

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Delegate handler registration to the underlying alerter."""
        self._alerter.add_handler(handler)

    @property
    def silence_manager(self) -> SilenceManager:
        return self._silence
