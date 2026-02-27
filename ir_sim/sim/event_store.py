import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class EventStore:
    def __init__(self, events_path: Path, incidents_path: Path):
        self.events_path = events_path
        self.incidents_path = incidents_path
        self.events_path.parent.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def append_jsonl(self, path: Path, obj: Dict[str, Any]) -> None:
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def read_jsonl(self, path: Path, limit: int = 200) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        lines = lines[-limit:]
        out: List[Dict[str, Any]] = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out

    def overwrite_jsonl(self, path: Path, objects: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w", encoding="utf-8") as f:
            for obj in objects:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # ---- events ----

    def emit_event(
        self,
        event_type: str,
        source: str,
        severity: str = "low",
        actor: Optional[Dict[str, Any]] = None,
        target: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        evt = {
            "ts": self.utc_now_iso(),
            "source": source,
            "event_type": event_type,
            "severity": severity,
            "actor": actor or {},
            "target": target or {},
            "details": details or {},
            "tags": tags or ["simulation"],
        }
        self.append_jsonl(self.events_path, evt)
        return evt

    def read_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.read_jsonl(self.events_path, limit=limit)

    # ---- incidents ----

    def new_incident(self, title: str, severity: str, rule_id: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        inc_id = f"inc-{int(time.time() * 1000)}"
        inc = {
            "id": inc_id,
            "created_ts": self.utc_now_iso(),
            "title": title,
            "severity": severity,
            "rule_id": rule_id,
            "status": "open",
            "actions": [],
            "evidence": evidence,
        }
        self.append_jsonl(self.incidents_path, inc)
        return inc

    def list_incidents(self, limit: int = 200) -> List[Dict[str, Any]]:
        incs = self.read_jsonl(self.incidents_path, limit=limit)
        incs.sort(key=lambda x: x.get("created_ts", ""), reverse=True)
        return incs

    def get_incident(self, inc_id: str) -> Optional[Dict[str, Any]]:
        incs = self.read_jsonl(self.incidents_path, limit=5000)
        for inc in incs:
            if inc.get("id") == inc_id:
                return inc
        return None

    def update_incident(self, inc_id: str, update_fn):
        incs = self.read_jsonl(self.incidents_path, limit=5000)
        changed = None
        for i, inc in enumerate(incs):
            if inc.get("id") == inc_id:
                inc = update_fn(inc)
                incs[i] = inc
                changed = inc
                break
        if changed is None:
            return None
        self.overwrite_jsonl(self.incidents_path, incs)
        return changed
