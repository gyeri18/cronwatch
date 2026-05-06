"""Tests for cronwatch.rate_limiter."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cronwatch.rate_limiter import RateLimiter, _now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JOB = "backup"
KIND = "missed"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestRateLimiterInit:
    def test_defaults_accepted(self):
        rl = RateLimiter()
        assert rl.capacity == 5
        assert rl.rate == 1.0

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            RateLimiter(capacity=0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate"):
            RateLimiter(rate=-1.0)


# ---------------------------------------------------------------------------
# allow()
# ---------------------------------------------------------------------------

class TestAllow:
    def test_first_call_allowed(self):
        rl = RateLimiter(capacity=3, rate=1.0)
        assert rl.allow(JOB, KIND) is True

    def test_exhausted_bucket_blocked(self):
        rl = RateLimiter(capacity=2, rate=0.0001)  # near-zero refill
        assert rl.allow(JOB, KIND) is True
        assert rl.allow(JOB, KIND) is True
        assert rl.allow(JOB, KIND) is False

    def test_different_keys_independent(self):
        rl = RateLimiter(capacity=1, rate=0.0001)
        assert rl.allow("job_a", KIND) is True
        assert rl.allow("job_b", KIND) is True  # separate bucket
        assert rl.allow("job_a", KIND) is False

    def test_tokens_refill_over_time(self):
        rl = RateLimiter(capacity=1, rate=10.0)  # 10 tokens/sec
        rl.allow(JOB, KIND)  # drain
        # Simulate 0.2 s passing → +2 tokens but capped at capacity=1
        with patch("cronwatch.rate_limiter._now", return_value=time.monotonic() + 0.2):
            assert rl.allow(JOB, KIND) is True


# ---------------------------------------------------------------------------
# available_tokens()
# ---------------------------------------------------------------------------

class TestAvailableTokens:
    def test_full_bucket_at_capacity(self):
        rl = RateLimiter(capacity=5, rate=1.0)
        assert rl.available_tokens(JOB, KIND) == pytest.approx(5.0, abs=0.1)

    def test_decreases_after_allow(self):
        rl = RateLimiter(capacity=5, rate=0.0001)
        rl.allow(JOB, KIND)
        assert rl.available_tokens(JOB, KIND) == pytest.approx(4.0, abs=0.05)


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_specific_key(self):
        rl = RateLimiter(capacity=1, rate=0.0001)
        rl.allow(JOB, KIND)  # drain
        rl.reset(JOB, KIND)
        assert rl.allow(JOB, KIND) is True  # bucket recreated full

    def test_reset_all(self):
        rl = RateLimiter(capacity=1, rate=0.0001)
        rl.allow("a", KIND)
        rl.allow("b", KIND)
        rl.reset()
        assert rl.allow("a", KIND) is True
        assert rl.allow("b", KIND) is True
