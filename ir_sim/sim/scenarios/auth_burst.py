import time
from sim.event_store import EventStore


def scenario_auth_burst(
    store: EventStore,
    user: str = "testuser",
    ip: str = "10.0.0.50",
    count: int = 20,
    delay_s: float = 0.03,
):
    for i in range(count):
        store.emit_event(
            event_type="auth.failure",
            source="scenario.auth_burst",
            severity="medium",
            actor={"user": user, "ip": ip},
            target={"service": "demo-app"},
            details={"attempt": i + 1},
            tags=["simulation", "auth"],
        )
        time.sleep(delay_s)
