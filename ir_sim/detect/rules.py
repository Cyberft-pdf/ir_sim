from typing import Dict, Any, List, Optional


def rule_auth_burst(events: List[Dict[str, Any]], threshold: int) -> Optional[Dict[str, Any]]:
    auth_fail = [e for e in events if e.get("event_type") == "auth.failure"]
    if len(auth_fail) < threshold:
        return None

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for e in auth_fail:
        user = e.get("actor", {}).get("user", "unknown")
        ip = e.get("actor", {}).get("ip", "unknown")
        buckets.setdefault(f"{user}|{ip}", []).append(e)

    for key, evts in buckets.items():
        if len(evts) >= threshold:
            user, ip = key.split("|", 1)
            return {
                "rule_id": "R-AUTH-BURST",
                "title": f"Suspicious auth failures burst (user={user}, ip={ip})",
                "severity": "high",
                "evidence": evts[-20:],
                "recommended_playbook": "mock_block_indicator",
            }
    return None


def rule_beacon(events: List[Dict[str, Any]], min_events: int, tolerance: float) -> Optional[Dict[str, Any]]:
    beacons = [e for e in events if e.get("event_type") == "net.beacon"]
    if len(beacons) < min_events:
        return None

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for e in beacons:
        host = e.get("actor", {}).get("host", "unknown")
        buckets.setdefault(host, []).append(e)

    for host, evts in buckets.items():
        if len(evts) < min_events:
            continue
        last = evts[-min_events:]
        intervals = [x.get("details", {}).get("interval_s") for x in last]
        if not all(isinstance(v, (int, float)) for v in intervals):
            continue
        if max(intervals) - min(intervals) <= tolerance:
            return {
                "rule_id": "R-BEACON",
                "title": f"Possible beaconing pattern (host={host})",
                "severity": "medium",
                "evidence": last,
                "recommended_playbook": "collect_artifacts",
            }
    return None


def build_rules(det_cfg: Dict[str, Any]):
    threshold = int(det_cfg.get("auth_burst_threshold", 10))
    min_events = int(det_cfg.get("beacon_min_events", 6))
    tolerance = float(det_cfg.get("beacon_interval_tolerance", 0.2))

    return [
        ("auth_burst", lambda ev: rule_auth_burst(ev, threshold)),
        ("beacon", lambda ev: rule_beacon(ev, min_events, tolerance)),
    ]
