"""Retry policy for alert delivery with exponential backoff."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    base_delay: float = 1.0   # seconds
    backoff_factor: float = 2.0
    max_delay: float = 60.0

    def delay_for(self, attempt: int) -> float:
        """Return the sleep duration before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


@dataclass
class RetryState:
    """Mutable state tracking retries for a single delivery."""

    policy: RetryPolicy
    attempts: int = 0
    last_error: Optional[str] = None
    succeeded: bool = False

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.policy.max_attempts

    def record_attempt(self, error: Optional[str] = None) -> None:
        self.attempts += 1
        if error is None:
            self.succeeded = True
            self.last_error = None
        else:
            self.last_error = error


def with_retry(
    fn: Callable[[], None],
    policy: RetryPolicy,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> RetryState:
    """Call *fn* up to *policy.max_attempts* times, sleeping between retries.

    Returns a :class:`RetryState` describing the outcome.
    """
    state = RetryState(policy=policy)
    while not state.exhausted:
        delay = policy.delay_for(state.attempts)
        if delay > 0:
            log.debug("Retry attempt %d — sleeping %.1fs", state.attempts, delay)
            sleep_fn(delay)
        try:
            fn()
            state.record_attempt()
            return state
        except Exception as exc:  # noqa: BLE001
            state.record_attempt(error=str(exc))
            log.warning(
                "Attempt %d/%d failed: %s",
                state.attempts,
                policy.max_attempts,
                exc,
            )
    return state
