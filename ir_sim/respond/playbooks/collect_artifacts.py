import json
from pathlib import Path
from typing import Dict, Any

from sim.event_store import EventStore


def playbook_collect_artifacts(incident: Dict[str, Any], artifacts_dir: Path, store: EventStore) -> Dict[str, Any]:
    inc_id = incident.get("id", "unknown")
    out_dir = artifacts_dir / inc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "evidence.json").open("w", encoding="utf-8") as f:
        json.dump(incident.get("evidence", []), f, ensure_ascii=False, indent=2)

    action = {
        "ts": store.utc_now_iso(),
        "type": "playbook",
        "name": "collect_artifacts",
        "status": "success",
        "details": {"saved_to": str(out_dir), "files": ["evidence.json"]},
    }
    incident.setdefault("actions", []).append(action)
    return incident
