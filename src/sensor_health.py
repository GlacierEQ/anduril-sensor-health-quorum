"""Sensor health quorum — suspend untrusted sensors from voting."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class SensorHealthQuorum:
    suspend_below: float = 0.4
    reinstate_above: float = 0.7
    scores: dict[str, float] = field(default_factory=dict)
    suspended: set[str] = field(default_factory=set)

    def report(self, reporter: str, subject: str, health: float) -> None:
        if not 0.0 <= health <= 1.0:
            raise ValueError("health")
        if reporter == subject:
            raise ValueError("SELF_REPORT_FORBIDDEN")
        # exponential moving blend
        prev = self.scores.get(subject, 0.5)
        self.scores[subject] = 0.6 * prev + 0.4 * health
        if self.scores[subject] < self.suspend_below:
            self.suspended.add(subject)
        elif self.scores[subject] >= self.reinstate_above:
            self.suspended.discard(subject)

    def can_vote(self, sensor_id: str) -> bool:
        return sensor_id not in self.suspended

    def fingerprint(self) -> str:
        return digest({"scores": self.scores, "suspended": sorted(self.suspended)})
