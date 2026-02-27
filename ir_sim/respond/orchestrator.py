from pathlib import Path
from typing import Dict, Any, Callable

from sim.event_store import EventStore


class Orchestrator:
    def __init__(self, store: EventStore, playbooks: Dict[str, Callable]):
        self.store = store
        self.playbooks = playbooks

    def run_playbook(self, inc_id: str, playbook_name: str, artifacts_dir: Path) -> bool:
        pb = self.playbooks.get(playbook_name)
        if not pb:
            return False

        def updater(inc: Dict[str, Any]) -> Dict[str, Any]:
            return pb(inc, artifacts_dir=artifacts_dir, store=self.store)

        updated = self.store.update_incident(inc_id, updater)
        return updated is not None
