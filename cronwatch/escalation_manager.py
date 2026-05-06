"""Manages escalation states for all watched jobs and fires alerts."""
from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime

from cronwatch.escalation import EscalationPolicy, EscalationState
from cronwatch.alerter import Alerter, Alert


class EscalationManager:
    """Coordinates escalation policies and states across jobs."""

    def __init__(
        self,
        alerter: Alerter,
        default_policy: Optional[EscalationPolicy] = None,
    ) -> None:
        self._alerter = alerter
        self._default_policy = default_policy or EscalationPolicy()
        self._states: Dict[str, EscalationState] = {}
        self._policies: Dict[str, EscalationPolicy] = {}

    def set_policy(self, job_name: str, policy: EscalationPolicy) -> None:
        """Override the escalation policy for a specific job."""
        self._policies[job_name] = policy

    def _get_policy(self, job_name: str) -> EscalationPolicy:
        return self._policies.get(job_name, self._default_policy)

    def _get_state(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState(job_name=job_name)
        return self._states[job_name]

    def on_failure(self, job_name: str, message: str, when: Optional[datetime] = None) -> bool:
        """Record a failure; returns True if an escalation alert was sent."""
        state = self._get_state(job_name)
        state.record_failure(when=when)
        policy = self._get_policy(job_name)
        if policy.should_escalate(state):
            alert = Alert(
                kind="escalation",
                job=job_name,
                message=message,
                extra={
                    "consecutive_failures": state.consecutive_failures,
                    "escalation_count": state.escalation_count + 1,
                },
            )
            self._alerter.send(alert)
            state.mark_escalated()
            return True
        return False

    def on_success(self, job_name: str) -> None:
        """Reset escalation state after a successful run."""
        state = self._get_state(job_name)
        state.record_success()

    def state_for(self, job_name: str) -> EscalationState:
        return self._get_state(job_name)

    def all_states(self) -> Dict[str, EscalationState]:
        return dict(self._states)
