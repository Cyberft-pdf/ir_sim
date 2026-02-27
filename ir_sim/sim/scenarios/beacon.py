import time
from sim.event_store import EventStore


def scenario_beacon(
    store: EventStore,
    host: str = "workstation-1",
    interval_s: float = 1.5,
    cycles: int = 8,
):
    for i in range(cycles):
        store.emit_event(
            event_type="net.beacon",
            source="scenario.beacon",
            severity="low",
            actor={"host": host},
            target={"url": "http://localhost/telemetry"},
            details={"cycle": i + 1, "interval_s": float(interval_s)},
            tags=["simulation", "network"],
        )
        time.sleep(interval_s)
