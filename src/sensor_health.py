"""Sensor-health quorum with correlation-aware authority and bounded recovery."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from statistics import fmean


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class HealthEvidence:
    reporter: str
    subject: str
    health: float
    fault_domain: str
    round_id: str | None


@dataclass(frozen=True)
class DomainWeight:
    fault_domain: str
    reporters: tuple[str, ...]
    domain_health: float
    effective_weight: float


@dataclass(frozen=True)
class HealthDecisionReceipt:
    subject: str
    observed_health: float
    smoothed_score: float
    independent_domains: int
    domain_weights: tuple[DomainWeight, ...]
    suspended_before: bool
    suspended_after: bool
    transition: str
    recovery_streak: int
    required_recovery_rounds: int
    reason: str

    def fingerprint(self) -> str:
        return digest(
            {
                "subject": self.subject,
                "observed_health": self.observed_health,
                "smoothed_score": self.smoothed_score,
                "independent_domains": self.independent_domains,
                "domain_weights": [
                    {
                        "fault_domain": row.fault_domain,
                        "reporters": list(row.reporters),
                        "domain_health": row.domain_health,
                        "effective_weight": row.effective_weight,
                    }
                    for row in self.domain_weights
                ],
                "suspended_before": self.suspended_before,
                "suspended_after": self.suspended_after,
                "transition": self.transition,
                "recovery_streak": self.recovery_streak,
                "required_recovery_rounds": self.required_recovery_rounds,
                "reason": self.reason,
            }
        )


@dataclass
class SensorHealthQuorum:
    suspend_below: float = 0.4
    reinstate_above: float = 0.7
    required_recovery_rounds: int = 2
    min_recovery_domains: int = 2
    scores: dict[str, float] = field(default_factory=dict)
    suspended: set[str] = field(default_factory=set)
    evidence: dict[str, dict[str, HealthEvidence]] = field(default_factory=dict)
    recovery_streaks: dict[str, int] = field(default_factory=dict)
    recovery_rounds_seen: dict[str, set[str]] = field(default_factory=dict)
    receipts: dict[str, HealthDecisionReceipt] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.suspend_below < self.reinstate_above <= 1.0:
            raise ValueError("thresholds")
        if self.required_recovery_rounds <= 0:
            raise ValueError("required_recovery_rounds")
        if self.min_recovery_domains <= 0:
            raise ValueError("min_recovery_domains")

    def _domain_weights(self, subject: str) -> tuple[DomainWeight, ...]:
        by_domain: dict[str, list[HealthEvidence]] = {}
        for report in self.evidence.get(subject, {}).values():
            by_domain.setdefault(report.fault_domain, []).append(report)
        if not by_domain:
            return ()
        weight = 1.0 / len(by_domain)
        rows = []
        for domain in sorted(by_domain):
            reports = by_domain[domain]
            rows.append(
                DomainWeight(
                    fault_domain=domain,
                    reporters=tuple(sorted(row.reporter for row in reports)),
                    domain_health=fmean(row.health for row in reports),
                    effective_weight=weight,
                )
            )
        return tuple(rows)

    def report(
        self,
        reporter: str,
        subject: str,
        health: float,
        *,
        fault_domain: str | None = None,
        round_id: str | None = None,
    ) -> HealthDecisionReceipt:
        if not reporter or not subject:
            raise ValueError("sensor_id")
        if not 0.0 <= health <= 1.0:
            raise ValueError("health")
        if reporter == subject:
            raise ValueError("SELF_REPORT_FORBIDDEN")
        domain = fault_domain or reporter
        if not domain:
            raise ValueError("fault_domain")
        if round_id == "":
            raise ValueError("round_id")

        self.evidence.setdefault(subject, {})[reporter] = HealthEvidence(
            reporter=reporter,
            subject=subject,
            health=health,
            fault_domain=domain,
            round_id=round_id,
        )
        weights = self._domain_weights(subject)
        observed = sum(row.domain_health * row.effective_weight for row in weights)
        previous = self.scores.get(subject, 0.5)
        score = 0.6 * previous + 0.4 * observed
        self.scores[subject] = score

        was_suspended = subject in self.suspended
        transition = "UNCHANGED"
        reason = "HEALTH_ACCEPTABLE"

        if score < self.suspend_below:
            self.suspended.add(subject)
            self.recovery_streaks[subject] = 0
            self.recovery_rounds_seen.setdefault(subject, set()).clear()
            transition = "SUSPEND" if not was_suspended else "HOLD_SUSPENDED"
            reason = "BELOW_SUSPEND_THRESHOLD"
        elif was_suspended:
            independent = len(weights)
            if score < self.reinstate_above:
                self.recovery_streaks[subject] = 0
                reason = "RECOVERY_THRESHOLD_NOT_MET"
            elif independent < self.min_recovery_domains:
                self.recovery_streaks[subject] = 0
                reason = "INSUFFICIENT_INDEPENDENT_DOMAINS"
            elif round_id is None:
                reason = "ROUND_ID_REQUIRED_FOR_RECOVERY"
            else:
                seen = self.recovery_rounds_seen.setdefault(subject, set())
                if round_id not in seen:
                    seen.add(round_id)
                    self.recovery_streaks[subject] = (
                        self.recovery_streaks.get(subject, 0) + 1
                    )
                if self.recovery_streaks[subject] >= self.required_recovery_rounds:
                    self.suspended.discard(subject)
                    transition = "REINSTATE"
                    reason = "RECOVERY_HYSTERESIS_SATISFIED"
                else:
                    transition = "HOLD_SUSPENDED"
                    reason = "RECOVERY_HYSTERESIS_INCOMPLETE"

        is_suspended = subject in self.suspended
        receipt = HealthDecisionReceipt(
            subject=subject,
            observed_health=observed,
            smoothed_score=score,
            independent_domains=len(weights),
            domain_weights=weights,
            suspended_before=was_suspended,
            suspended_after=is_suspended,
            transition=transition,
            recovery_streak=self.recovery_streaks.get(subject, 0),
            required_recovery_rounds=self.required_recovery_rounds,
            reason=reason,
        )
        self.receipts[subject] = receipt
        return receipt

    def can_vote(self, sensor_id: str) -> bool:
        return sensor_id not in self.suspended

    def last_receipt(self, sensor_id: str) -> HealthDecisionReceipt | None:
        return self.receipts.get(sensor_id)

    def fingerprint(self) -> str:
        return digest(
            {
                "scores": self.scores,
                "suspended": sorted(self.suspended),
                "recovery_streaks": self.recovery_streaks,
                "evidence": {
                    subject: {
                        reporter: {
                            "health": row.health,
                            "fault_domain": row.fault_domain,
                            "round_id": row.round_id,
                        }
                        for reporter, row in sorted(rows.items())
                    }
                    for subject, rows in sorted(self.evidence.items())
                },
            }
        )
