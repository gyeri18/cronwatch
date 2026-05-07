"""Tests for cronwatch.suppression."""

import pytest

from cronwatch.suppression import SuppressionManager, SuppressionRule


# ---------------------------------------------------------------------------
# SuppressionRule
# ---------------------------------------------------------------------------

class TestSuppressionRule:
    def test_exact_job_name_matches(self):
        rule = SuppressionRule(job_pattern="backup")
        assert rule.matches("backup", "missed") is True

    def test_wildcard_job_pattern_matches(self):
        rule = SuppressionRule(job_pattern="backup_*")
        assert rule.matches("backup_daily", "missed") is True

    def test_wildcard_does_not_match_unrelated(self):
        rule = SuppressionRule(job_pattern="backup_*")
        assert rule.matches("report_daily", "missed") is False

    def test_kind_filter_matches_included_kind(self):
        rule = SuppressionRule(job_pattern="*", kinds={"missed"})
        assert rule.matches("any_job", "missed") is True

    def test_kind_filter_excludes_other_kind(self):
        rule = SuppressionRule(job_pattern="*", kinds={"missed"})
        assert rule.matches("any_job", "slow") is False

    def test_none_kinds_matches_all_kinds(self):
        rule = SuppressionRule(job_pattern="*", kinds=None)
        assert rule.matches("any_job", "slow") is True
        assert rule.matches("any_job", "missed") is True

    def test_multiple_kinds_in_set(self):
        rule = SuppressionRule(job_pattern="etl", kinds={"missed", "slow"})
        assert rule.matches("etl", "missed") is True
        assert rule.matches("etl", "slow") is True
        assert rule.matches("etl", "error") is False

    def test_reason_stored(self):
        rule = SuppressionRule(job_pattern="*", reason="maintenance window")
        assert rule.reason == "maintenance window"


# ---------------------------------------------------------------------------
# SuppressionManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager() -> SuppressionManager:
    return SuppressionManager()


class TestSuppressionManager:
    def test_empty_manager_never_suppresses(self, manager):
        assert manager.is_suppressed("backup", "missed") is False

    def test_add_rule_suppresses_matching_alert(self, manager):
        manager.add_rule(SuppressionRule(job_pattern="backup"))
        assert manager.is_suppressed("backup", "missed") is True

    def test_add_rule_does_not_suppress_unmatched(self, manager):
        manager.add_rule(SuppressionRule(job_pattern="backup"))
        assert manager.is_suppressed("report", "missed") is False

    def test_remove_rule_lifts_suppression(self, manager):
        rule = SuppressionRule(job_pattern="backup")
        manager.add_rule(rule)
        manager.remove_rule(rule)
        assert manager.is_suppressed("backup", "missed") is False

    def test_matching_rules_returns_correct_subset(self, manager):
        r1 = SuppressionRule(job_pattern="backup_*")
        r2 = SuppressionRule(job_pattern="report_*")
        manager.add_rule(r1)
        manager.add_rule(r2)
        result = manager.matching_rules("backup_daily", "missed")
        assert result == [r1]

    def test_matching_rules_empty_when_no_match(self, manager):
        manager.add_rule(SuppressionRule(job_pattern="backup"))
        assert manager.matching_rules("report", "missed") == []

    def test_rules_property_returns_copy(self, manager):
        rule = SuppressionRule(job_pattern="*")
        manager.add_rule(rule)
        rules = manager.rules
        rules.clear()
        assert len(manager.rules) == 1
