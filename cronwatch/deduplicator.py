"""Alert deduplication — suppress identical alerts within a cooldown window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatch.alerter import Alert


def _now() -> float:
    return time.monotonic()


def _alert_key(alert: Alert) -> str:
    """Stable hash key derived from alert kind, job name, and message."""
    raw = f"{alert.kind}|{alert.job_name}|{alert.message}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class _Entry:
    first_seen: float
    last_seen: float
    count: int = 1


class Deduplicator:
    """Wraps an alert handler and suppresses duplicate alerts within *cooldown* seconds.

    An alert is considered a duplicate when its (kind, job_name, message) triple
    matches one already seen within the cooldown window.  After the window expires
    the next occurrence is forwarded and the window resets.
    """

    def __init__(
        self,
        handler: Callable[[Alert], None],
        cooldown: float = 300.0,
        clock: Callable[[], float] = _now,
    ) -> None:
        if cooldown < 0:
            raise ValueError("cooldown must be >= 0")
        self._handler = handler
        self._cooldown = cooldown
        self._clock = clock
        self._seen: Dict[str, _Entry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> bool:
        """Forward *alert* to the wrapped handler unless it is a duplicate.

        Returns True when the alert was forwarded, False when suppressed.
        """
        key = _alert_key(alert)
        now = self._clock()
        entry = self._seen.get(key)

        if entry is None or (now - entry.last_seen) >= self._cooldown:
            self._seen[key] = _Entry(first_seen=now, last_seen=now)
            self._handler(alert)
            return True

        # Still within cooldown — suppress and update tracking.
        entry.last_seen = now
        entry.count += 1
        return False

    def suppressed_count(self, alert: Alert) -> int:
        """Return how many times *alert* has been suppressed (not forwarded)."""
        key = _alert_key(alert)
        entry = self._seen.get(key)
        if entry is None:
            return 0
        return max(0, entry.count - 1)

    def reset(self, alert: Optional[Alert] = None) -> None:
        """Clear dedup state for *alert*, or all state if *alert* is None."""
        if alert is None:
            self._seen.clear()
        else:
            self._seen.pop(_alert_key(alert), None)
