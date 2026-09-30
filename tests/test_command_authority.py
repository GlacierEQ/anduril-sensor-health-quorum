"""Auto-generated tests for Command Authority & Mission Assurance."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import time
from anduril_sensor_health_quorum.core import AuthLevel, CommandRequest, DualKeyGate, CommandVerdict, SensorQuorum

def test_command_fingerprint():
    cmd = CommandRequest("C001", "operator1", AuthLevel.COMMANDER, "LAUNCH")
    assert len(cmd.fingerprint) == 16

def test_dual_key_requires_two():
    gate = DualKeyGate(expiry_seconds=60.0)
    cmd = CommandRequest("C001", "op1", AuthLevel.COMMANDER, "LAUNCH")
    assert gate.approve(cmd, "approver_a") == CommandVerdict.PENDING
    assert gate.approve(cmd, "approver_b") == CommandVerdict.APPROVED

def test_dual_key_same_person_blocked():
    gate = DualKeyGate(expiry_seconds=60.0)
    cmd = CommandRequest("C002", "op1", AuthLevel.COMMANDER, "ARM")
    gate.approve(cmd, "approver_a")
    assert gate.approve(cmd, "approver_a") == CommandVerdict.PENDING

def test_low_auth_denied():
    gate = DualKeyGate()
    cmd = CommandRequest("C003", "op1", AuthLevel.OBSERVER, "PEEK")
    assert gate.approve(cmd, "anyone") == CommandVerdict.DENIED

def test_sensor_quorum():
    sq = SensorQuorum(required=3, total=5)
    sq.vote("s1", True)
    sq.vote("s2", True)
    assert not sq.quorum_reached
    sq.vote("s3", True)
    assert sq.quorum_reached

def test_sensor_quorum_disagreement():
    sq = SensorQuorum(required=3, total=5)
    sq.vote("s1", True)
    sq.vote("s2", False)
    sq.vote("s3", True)
    sq.vote("s4", False)
    assert not sq.quorum_reached

def test_consensus_ratio():
    sq = SensorQuorum(required=2, total=4)
    sq.vote("s1", True)
    sq.vote("s2", True)
    sq.vote("s3", False)
    sq.vote("s4", True)
    assert abs(sq.consensus_ratio - 0.75) < 0.01

