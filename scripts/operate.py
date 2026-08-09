#!/usr/bin/env python3
"""Cold-start operability exercise — real SensorHealthQuorum path."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sensor_health import SensorHealthQuorum

def main() -> int:
    q = SensorHealthQuorum(suspend_below=0.4, reinstate_above=0.7)
    q.report("s1", "s2", 0.1)
    q.report("s3", "s2", 0.1)
    can = q.can_vote("s2")
    fp = q.fingerprint()
    out = {"sensor": "s2", "can_vote": can, "expected_can_vote": False, "fingerprint": fp, "ok": can is False}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
