from typing import Dict, Any, List, Tuple

from sim.event_store import EventStore


class DetectionEngine:
    def __init__(self, store: EventStore, rules: List[Tuple[str, callable]]):
        self.store = store
        self.rules = rules

    def detect_once(self) -> List[Dict[str, Any]]:
        events = self.store.read_events(limit=500)
        detections: List[Dict[str, Any]] = []
        for _name, fn in self.rules:
            hit = fn(events)
            if hit:
                detections.append(hit)
        return detections

    def create_incidents_from_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        existing = self.store.list_incidents(limit=50)
        existing_keys = set((i.get("rule_id"), i.get("title")) for i in existing)

        for d in detections:
            key = (d["rule_id"], d["title"])
            if key in existing_keys:
                continue
            created.append(self.store.new_incident(d["title"], d["severity"], d["rule_id"], d["evidence"]))
        return created
