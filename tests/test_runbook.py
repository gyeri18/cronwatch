"""Tests for RunbookRegistry and RunbookAlerter."""
import pytest

from cronwatch.alerter import Alert, Alerter
from cronwatch.alerter_runbook import RunbookAlerter
from cronwatch.runbook import RunbookEntry, RunbookRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> RunbookRegistry:
    return RunbookRegistry()


@pytest.fixture()
def entry() -> RunbookEntry:
    return RunbookEntry(
        kind="missed",
        title="Missed Job Runbook",
        steps=["Check cron daemon", "Review logs"],
        url="https://wiki.example.com/runbooks/missed",
    )


# ---------------------------------------------------------------------------
# RunbookEntry
# ---------------------------------------------------------------------------

class TestRunbookEntry:
    def test_to_dict_roundtrip(self, entry):
        d = entry.to_dict()
        assert d["kind"] == "missed"
        assert d["title"] == "Missed Job Runbook"
        assert d["url"] == "https://wiki.example.com/runbooks/missed"
        assert len(d["steps"]) == 2
        assert d["job"] is None

    def test_to_dict_with_job(self):
        e = RunbookEntry(kind="slow", title="Slow", job="backup")
        assert e.to_dict()["job"] == "backup"


# ---------------------------------------------------------------------------
# RunbookRegistry
# ---------------------------------------------------------------------------

class TestRunbookRegistry:
    def test_lookup_returns_none_when_empty(self, registry):
        assert registry.lookup("missed") is None

    def test_lookup_finds_wildcard(self, registry, entry):
        registry.register(entry)
        result = registry.lookup("missed")
        assert result is entry

    def test_job_specific_beats_wildcard(self, registry, entry):
        registry.register(entry)  # wildcard
        specific = RunbookEntry(kind="missed", title="Job-specific", job="backup")
        registry.register(specific)
        assert registry.lookup("missed", "backup") is specific
        assert registry.lookup("missed", "other") is entry

    def test_all_for_kind(self, registry, entry):
        registry.register(entry)
        registry.register(RunbookEntry(kind="slow", title="Slow"))
        assert len(registry.all_for_kind("missed")) == 1
        assert len(registry.all_for_kind("slow")) == 1
        assert len(registry.all_for_kind("unknown")) == 0

    def test_annotate_adds_fields(self, registry, entry):
        registry.register(entry)
        result = registry.annotate("missed", None, {"foo": "bar"})
        assert result["foo"] == "bar"
        assert result["runbook_title"] == "Missed Job Runbook"
        assert "runbook_url" in result
        assert "runbook_steps" in result

    def test_annotate_does_not_overwrite(self, registry, entry):
        registry.register(entry)
        result = registry.annotate("missed", None, {"runbook_title": "custom"})
        assert result["runbook_title"] == "custom"

    def test_annotate_no_entry_returns_extra_unchanged(self, registry):
        extra = {"x": 1}
        assert registry.annotate("unknown", None, extra) == extra


# ---------------------------------------------------------------------------
# RunbookAlerter
# ---------------------------------------------------------------------------

class TestRunbookAlerter:
    def _make(self):
        reg = RunbookRegistry()
        reg.register(RunbookEntry(kind="missed", title="Fix missed", url="http://x"))
        base = Alerter()
        received: list = []
        base.add_handler(received.append)
        alerter = RunbookAlerter(base, reg)
        return alerter, received

    def test_enriches_extra(self):
        alerter, received = self._make()
        alerter.send(Alert(kind="missed", job="j", message="m"))
        assert received[0].extra["runbook_title"] == "Fix missed"
        assert received[0].extra["runbook_url"] == "http://x"

    def test_unknown_kind_passes_through(self):
        alerter, received = self._make()
        alerter.send(Alert(kind="slow", job="j", message="m"))
        assert "runbook_title" not in received[0].extra

    def test_registry_property(self):
        reg = RunbookRegistry()
        alerter = RunbookAlerter(Alerter(), reg)
        assert alerter.registry is reg
