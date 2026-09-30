"""Command Authority & Mission Assurance — Core Module"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

class AuthLevel(Enum):
    OBSERVER = auto()
    OPERATOR = auto()
    COMMANDER = auto()
    FLIGHT_DIRECTOR = auto()

class CommandVerdict(Enum):
    APPROVED = auto()
    DENIED = auto()
    PENDING = auto()
    EXPIRED = auto()

@dataclass(frozen=True)
class CommandRequest:
    """An authorized command request requiring dual-key approval."""
    command_id: str
    issuer: str
    auth_level: AuthLevel
    payload: str
    timestamp: float = field(default_factory=time.time)

    @property
    def fingerprint(self) -> str:
        raw = f"{{self.command_id}}:{{self.issuer}}:{{self.payload}}:{{self.timestamp}}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DualKeyGate:
    """Requires two independent approvals to authorize a command."""

    def __init__(self, expiry_seconds: float = 300.0):
        self.expiry = expiry_seconds
        self._approvals: dict[str, list[str]] = {{}}  # cmd_id -> [approver1, ...]

    def approve(self, cmd: CommandRequest, approver: str) -> CommandVerdict:
        if cmd.auth_level.value < AuthLevel.COMMANDER.value:
            return CommandVerdict.DENIED

        elapsed = time.time() - cmd.timestamp
        if elapsed > self.expiry:
            return CommandVerdict.EXPIRED

        if cmd.command_id not in self._approvals:
            self._approvals[cmd.command_id] = []

        if approver in self._approvals[cmd.command_id]:
            return CommandVerdict.PENDING  # same person can't approve twice

        self._approvals[cmd.command_id].append(approver)

        if len(self._approvals[cmd.command_id]) >= 2:
            return CommandVerdict.APPROVED
        return CommandVerdict.PENDING


class SensorQuorum:
    """Requires N-of-M sensor agreement before action."""

    def __init__(self, required: int, total: int):
        assert required <= total
        self.required = required
        self.total = total
        self._votes: dict[str, bool] = {{}}

    def vote(self, sensor_id: str, agrees: bool) -> None:
        self._votes[sensor_id] = agrees

    @property
    def quorum_reached(self) -> bool:
        agrees = sum(1 for v in self._votes.values() if v)
        return agrees >= self.required

    @property
    def consensus_ratio(self) -> float:
        if not self._votes:
            return 0.0
        return sum(1 for v in self._votes.values() if v) / len(self._votes)

