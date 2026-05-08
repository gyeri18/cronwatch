"""Tests for cronwatch.routing and cronwatch.alerter_routed."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from cronwatch.alerter import Alert
from cronwatch.alerter_routed import RoutedAlerter
from cronwatch.routing import AlertRouter, RoutingRule


def _alert(job: str = "backup", kind: str = "missed") -> Alert:
    return Alert(job=job, kind=kind, message="test", ts=datetime(2024, 1, 1, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------
# RoutingRule.matches
# ---------------------------------------------------------------------------

class TestRoutingRule:
    def test_no_filters_matches_anything(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append)
        assert rule.matches(_alert()) is True

    def test_job_pattern_matches_wildcard(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append, job_pattern="back*")
        assert rule.matches(_alert(job="backup")) is True

    def test_job_pattern_rejects_non_match(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append, job_pattern="billing-*")
        assert rule.matches(_alert(job="backup")) is False

    def test_kind_filter_matches_exact(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append, kind_filter="missed")
        assert rule.matches(_alert(kind="missed")) is True

    def test_kind_filter_rejects_other_kind(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append, kind_filter="slow")
        assert rule.matches(_alert(kind="missed")) is False

    def test_both_filters_must_match(self):
        received: List[Alert] = []
        rule = RoutingRule(handler=received.append, job_pattern="back*", kind_filter="slow")
        assert rule.matches(_alert(job="backup", kind="missed")) is False
        assert rule.matches(_alert(job="backup", kind="slow")) is True


# ---------------------------------------------------------------------------
# AlertRouter fan-out
# ---------------------------------------------------------------------------

class TestAlertRouterFanOut:
    def test_all_matching_rules_fire(self):
        received_a: List[Alert] = []
        received_b: List[Alert] = []
        router = AlertRouter()
        router.add_rule(received_a.append)
        router.add_rule(received_b.append)
        count = router.route(_alert())
        assert count == 2
        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_non_matching_rule_skipped(self):
        received: List[Alert] = []
        router = AlertRouter()
        router.add_rule(received.append, kind_filter="slow")
        count = router.route(_alert(kind="missed"))
        assert count == 0
        assert received == []

    def test_first_match_only_stops_after_first(self):
        received_a: List[Alert] = []
        received_b: List[Alert] = []
        router = AlertRouter(first_match_only=True)
        router.add_rule(received_a.append)
        router.add_rule(received_b.append)
        count = router.route(_alert())
        assert count == 1
        assert len(received_a) == 1
        assert len(received_b) == 0

    def test_rules_property_returns_copy(self):
        router = AlertRouter()
        router.add_rule(lambda a: None)
        rules = router.rules
        rules.clear()
        assert len(router.rules) == 1


# ---------------------------------------------------------------------------
# RoutedAlerter
# ---------------------------------------------------------------------------

class TestRoutedAlerter:
    def test_send_returns_dispatch_count(self):
        received: List[Alert] = []
        ra = RoutedAlerter()
        ra.add_handler(received.append)
        assert ra.send(_alert()) == 1

    def test_kind_filter_forwarded_to_router(self):
        slow: List[Alert] = []
        missed: List[Alert] = []
        ra = RoutedAlerter()
        ra.add_handler(slow.append, kind_filter="slow")
        ra.add_handler(missed.append, kind_filter="missed")
        ra.send(_alert(kind="slow"))
        assert len(slow) == 1
        assert len(missed) == 0

    def test_job_pattern_forwarded_to_router(self):
        received: List[Alert] = []
        ra = RoutedAlerter()
        ra.add_handler(received.append, job_pattern="billing-*")
        ra.send(_alert(job="backup"))
        assert received == []
        ra.send(_alert(job="billing-monthly"))
        assert len(received) == 1

    def test_router_property_exposed(self):
        ra = RoutedAlerter()
        assert isinstance(ra.router, AlertRouter)
