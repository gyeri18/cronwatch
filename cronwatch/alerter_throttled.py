"""Thin wrapper around Alerter that gates dispatch through a RateLimiter."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatch.alerter import Alert, Alerter
from cronwatch.rate_limiter import RateLimiter


class ThrottledAlerter:
    """Wraps an :class:`Alerter` and drops alerts that exceed the rate limit.

    Parameters
    ----------
    alerter:
        Underlying alerter used to dispatch allowed alerts.
    rate_limiter:
        Token-bucket limiter.  A fresh :class:`RateLimiter` with default
        settings is created when *None* is supplied.
    """

    def __init__(
        self,
        alerter: Alerter,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self._alerter = alerter
        self._limiter = rate_limiter if rate_limiter is not None else RateLimiter()
        self.dropped: int = 0  # count of suppressed alerts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(
        self,
        kind: str,
        job: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an alert if the rate limiter allows it.

        Returns
        -------
        bool
            ``True`` if the alert was dispatched, ``False`` if suppressed.
        """
        if self._limiter.allow(job, kind):
            alert = Alert(kind=kind, job=job, message=message, extra=extra or {})
            self._alerter.dispatch(alert)
            return True
        self.dropped += 1
        return False

    def available_tokens(self, job: str, kind: str) -> float:
        """Expose remaining tokens for the given (job, kind) pair."""
        return self._limiter.available_tokens(job, kind)

    def reset_limiter(self, job: Optional[str] = None, kind: Optional[str] = None) -> None:
        """Delegate to the underlying rate-limiter's reset."""
        if job is not None and kind is not None:
            self._limiter.reset(job, kind)
        else:
            self._limiter.reset()
        self.dropped = 0
