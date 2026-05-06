"""Tests for cronwatch.fingerprint."""

import pytest

from cronwatch.fingerprint import (
    AlertFingerprint,
    FingerprintRegistry,
    compute_fingerprint,
)


# ---------------------------------------------------------------------------
# compute_fingerprint
# ---------------------------------------------------------------------------

class TestComputeFingerprint:
    def test_returns_fingerprint_instance(self):
        fp = compute_fingerprint("backup", "missed")
        assert isinstance(fp, AlertFingerprint)

    def test_job_and_kind_stored(self):
        fp = compute_fingerprint("backup", "slow")
        assert fp.job == "backup"
        assert fp.kind == "slow"

    def test_digest_is_hex_string(self):
        fp = compute_fingerprint("backup", "missed")
        int(fp.digest, 16)  # raises if not valid hex

    def test_same_inputs_produce_same_digest(self):
        fp1 = compute_fingerprint("backup", "missed", {"threshold": 60})
        fp2 = compute_fingerprint("backup", "missed", {"threshold": 60})
        assert fp1.digest == fp2.digest

    def test_different_job_produces_different_digest(self):
        fp1 = compute_fingerprint("backup", "missed")
        fp2 = compute_fingerprint("restore", "missed")
        assert fp1.digest != fp2.digest

    def test_different_kind_produces_different_digest(self):
        fp1 = compute_fingerprint("backup", "missed")
        fp2 = compute_fingerprint("backup", "slow")
        assert fp1.digest != fp2.digest

    def test_extra_order_does_not_affect_digest(self):
        fp1 = compute_fingerprint("j", "k", {"a": 1, "b": 2})
        fp2 = compute_fingerprint("j", "k", {"b": 2, "a": 1})
        assert fp1.digest == fp2.digest

    def test_str_contains_short_digest(self):
        fp = compute_fingerprint("backup", "missed")
        s = str(fp)
        assert fp.digest[:12] in s
        assert "backup" in s
        assert "missed" in s


# ---------------------------------------------------------------------------
# FingerprintRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> FingerprintRegistry:
    return FingerprintRegistry()


@pytest.fixture()
def fp() -> AlertFingerprint:
    return compute_fingerprint("backup", "missed")


class TestFingerprintRegistry:
    def test_unseen_fingerprint_returns_false(self, registry, fp):
        assert registry.seen(fp) is False

    def test_after_record_seen_returns_true(self, registry, fp):
        registry.record(fp)
        assert registry.seen(fp) is True

    def test_count_zero_before_record(self, registry, fp):
        assert registry.count(fp) == 0

    def test_count_increments_on_each_record(self, registry, fp):
        registry.record(fp)
        registry.record(fp)
        assert registry.count(fp) == 2

    def test_record_returns_new_count(self, registry, fp):
        assert registry.record(fp) == 1
        assert registry.record(fp) == 2

    def test_clear_removes_fingerprint(self, registry, fp):
        registry.record(fp)
        registry.clear(fp)
        assert registry.seen(fp) is False
        assert registry.count(fp) == 0

    def test_clear_all_resets_registry(self, registry, fp):
        other = compute_fingerprint("restore", "slow")
        registry.record(fp)
        registry.record(other)
        registry.clear_all()
        assert registry.count(fp) == 0
        assert registry.count(other) == 0

    def test_independent_fingerprints_tracked_separately(self, registry):
        fp1 = compute_fingerprint("j1", "missed")
        fp2 = compute_fingerprint("j2", "missed")
        registry.record(fp1)
        assert registry.count(fp2) == 0
