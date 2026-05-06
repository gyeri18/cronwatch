"""Tests for cronwatch.retry."""

from __future__ import annotations

import pytest
from unittest.mock import call, patch

from cronwatch.retry import RetryPolicy, RetryState, with_retry


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

class TestRetryPolicy:
    def test_delay_zero_for_first_attempt(self):
        policy = RetryPolicy(base_delay=2.0)
        assert policy.delay_for(0) == 0.0

    def test_delay_base_for_second_attempt(self):
        policy = RetryPolicy(base_delay=2.0, backoff_factor=2.0)
        assert policy.delay_for(1) == 2.0

    def test_delay_grows_exponentially(self):
        policy = RetryPolicy(base_delay=1.0, backoff_factor=3.0, max_delay=100.0)
        assert policy.delay_for(2) == 3.0
        assert policy.delay_for(3) == 9.0

    def test_delay_capped_at_max(self):
        policy = RetryPolicy(base_delay=10.0, backoff_factor=10.0, max_delay=50.0)
        assert policy.delay_for(4) == 50.0


# ---------------------------------------------------------------------------
# RetryState
# ---------------------------------------------------------------------------

class TestRetryState:
    def _make(self, max_attempts: int = 3) -> RetryState:
        return RetryState(policy=RetryPolicy(max_attempts=max_attempts))

    def test_not_exhausted_initially(self):
        state = self._make()
        assert not state.exhausted

    def test_exhausted_after_max_attempts(self):
        state = self._make(max_attempts=2)
        state.record_attempt(error="boom")
        state.record_attempt(error="boom")
        assert state.exhausted

    def test_succeeded_on_clean_record(self):
        state = self._make()
        state.record_attempt()
        assert state.succeeded
        assert state.last_error is None

    def test_last_error_stored_on_failure(self):
        state = self._make()
        state.record_attempt(error="timeout")
        assert state.last_error == "timeout"
        assert not state.succeeded


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

class TestWithRetry:
    def _no_sleep(self, _: float) -> None:
        pass

    def test_succeeds_on_first_try(self):
        calls = []
        policy = RetryPolicy(max_attempts=3, base_delay=0.0)
        state = with_retry(lambda: calls.append(1), policy, sleep_fn=self._no_sleep)
        assert state.succeeded
        assert state.attempts == 1
        assert len(calls) == 1

    def test_retries_on_failure_then_succeeds(self):
        results = [ValueError("fail"), None]

        def flaky():
            r = results.pop(0)
            if r is not None:
                raise r

        policy = RetryPolicy(max_attempts=3, base_delay=0.0)
        state = with_retry(flaky, policy, sleep_fn=self._no_sleep)
        assert state.succeeded
        assert state.attempts == 2

    def test_exhausts_all_attempts(self):
        policy = RetryPolicy(max_attempts=3, base_delay=0.0)
        state = with_retry(
            lambda: (_ for _ in ()).throw(RuntimeError("always fails")),
            policy,
            sleep_fn=self._no_sleep,
        )
        assert not state.succeeded
        assert state.attempts == 3
        assert state.exhausted

    def test_sleep_called_between_retries(self):
        slept: list[float] = []
        policy = RetryPolicy(max_attempts=3, base_delay=1.0, backoff_factor=2.0)

        def always_fail():
            raise RuntimeError("x")

        with_retry(always_fail, policy, sleep_fn=slept.append)
        # First attempt: no sleep; second: 1.0 s; third: 2.0 s
        assert slept == [1.0, 2.0]
