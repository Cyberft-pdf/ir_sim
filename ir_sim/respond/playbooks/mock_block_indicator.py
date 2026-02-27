from pathlib import Path
from typing import Dict, Any, Optional

from sim.event_store import EventStore


def _extract_ip(incident: Dict[str, Any]) -> Optional[str]:
    for e in reversed(incident.get("evidence", [])):
        ip = (e.get("actor") or {}).get("ip")
        if ip:
            return ip
    return None


def playbook_mock_block_indicator(incident: Dict[str, Any], artifacts_dir: Path, store: EventStore) -> Dict[str, Any]:
    ip = _extract_ip(incident)

    action = {
        "ts": store.utc_now_iso(),
        "type": "playbook",
        "name": "mock_block_indicator",
        "status": "success",
        "details": {
            "note": "Mock action only (no real firewall change).",
            "blocked_ip": ip or "unknown",
        },
    }
    incident.setdefault("actions", []).append(action)
    incident["status"] = "contained"
    return incident
