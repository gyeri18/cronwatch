"""Alert sender that suppresses duplicate alerts using fingerprinting."""

from __future__ import annotations

from typing import Any, Callable

from cronwatch.alerter import Alert
from cronwatch.fingerprint import (
    AlertFingerprint,
    FingerprintRegistry,
    compute_fingerprint,
)

Handler = Callable[[Alert], None]


class FingerprintedAlerter:
    """Wraps a list of handlers and skips alerts whose fingerprint was already sent.

    Parameters
    ----------
    max_repeats:
        Maximum number of times the *same* fingerprint will be forwarded to
        handlers.  ``0`` means send only once; ``None`` means unlimited.
    extra_keys:
        Names of keys inside ``Alert.extra`` that should be included in the
        fingerprint digest.  Volatile values (e.g. timestamps) should be
        omitted to keep the fingerprint stable across repeated fires.
    """

    def __init__(
        self,
        max_repeats: int | None = 0,
        extra_keys: list[str] | None = None,
    ) -> None:
        self._handlers: list[Handler] = []
        self._registry = FingerprintRegistry()
        self._max_repeats = max_repeats
        self._extra_keys: list[str] = extra_keys or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_handler(self, handler: Handler) -> None:
        """Register a downstream alert handler."""
        self._handlers.append(handler)

    def send(self, alert: Alert) -> bool:
        """Forward *alert* to handlers unless it is a suppressed duplicate.

        Returns
        -------
        bool
            ``True`` if the alert was forwarded, ``False`` if suppressed.
        """
        fp = self._fingerprint(alert)
        count = self._registry.count(fp)

        if self._max_repeats is not None and count > self._max_repeats:
            return False

        self._registry.record(fp)
        for handler in self._handlers:
            handler(alert)
        return True

    def reset(self, job: str, kind: str, extra: dict[str, Any] | None = None) -> None:
        """Clear the fingerprint for *job*/*kind* so the next send is forwarded."""
        fp = compute_fingerprint(job, kind, self._stable_extra(extra or {}))
        self._registry.clear(fp)

    def reset_all(self) -> None:
        """Clear all stored fingerprints."""
        self._registry.clear_all()

    @property
    def registry(self) -> FingerprintRegistry:
        """Expose the underlying registry (read-only use intended)."""
        return self._registry

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _stable_extra(self, extra: dict[str, Any]) -> dict[str, Any]:
        return {k: extra[k] for k in self._extra_keys if k in extra}

    def _fingerprint(self, alert: Alert) -> AlertFingerprint:
        return compute_fingerprint(
            alert.job, alert.kind, self._stable_extra(alert.extra)
        )
