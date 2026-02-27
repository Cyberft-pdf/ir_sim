import threading
from pathlib import Path
from typing import Dict, Any

import yaml
from flask import Flask, render_template, redirect, url_for, request, jsonify

from sim.event_store import EventStore
from sim.scenarios.auth_burst import scenario_auth_burst
from sim.scenarios.beacon import scenario_beacon

from detect.engine import DetectionEngine
from detect.rules import build_rules

from respond.orchestrator import Orchestrator
from respond.playbooks.collect_artifacts import playbook_collect_artifacts
from respond.playbooks.mock_block_indicator import playbook_mock_block_indicator


def load_config() -> Dict[str, Any]:
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
APP_NAME = config["app"]["name"]

DATA_DIR = Path(config["storage"]["data_dir"])
EVENTS_FILE = DATA_DIR / config["storage"]["events_file"]
INCIDENTS_FILE = DATA_DIR / config["storage"]["incidents_file"]
ARTIFACTS_DIR = DATA_DIR / config["storage"]["artifacts_dir"]

DATA_DIR.mkdir(exist_ok=True)
( DATA_DIR / ".gitkeep").touch(exist_ok=True)

store = EventStore(events_path=EVENTS_FILE, incidents_path=INCIDENTS_FILE)
rules = build_rules(config["detection"])
detector = DetectionEngine(store=store, rules=rules)

playbooks = {
    "collect_artifacts": playbook_collect_artifacts,
    "mock_block_indicator": playbook_mock_block_indicator,
}
orchestrator = Orchestrator(store=store, playbooks=playbooks)

SCENARIOS = {
    "auth_burst": {
        "title": "Auth failure burst (safe)",
        "description": "Generuje hodně neúspěšných přihlášení do logu; testuje detekci a containment.",
        "fn": scenario_auth_burst,
    },
    "beacon": {
        "title": "Beacon pattern (safe)",
        "description": "Generuje pravidelné beacon události; testuje korelaci a sběr artifactů.",
        "fn": scenario_beacon,
    },
}

RUN_LOCK = threading.Lock()
LAST_RUN = {"status": "idle", "ts": None, "message": ""}

app = Flask(__name__)


def run_scenario_and_detect(name: str, params: Dict[str, Any]) -> None:
    global LAST_RUN
    with RUN_LOCK:
        LAST_RUN = {"status": "running", "ts": store.utc_now_iso(), "message": f"Running scenario: {name}"}
    try:
        scenario = SCENARIOS.get(name)
        if not scenario:
            raise ValueError("Unknown scenario")

        scenario["fn"](store=store, **params)

        detections = detector.detect_once()
        created = detector.create_incidents_from_detections(detections)

        with RUN_LOCK:
            LAST_RUN = {
                "status": "done",
                "ts": store.utc_now_iso(),
                "message": f"Scenario {name} finished. Detections={len(detections)}, new incidents={len(created)}",
            }
    except Exception as e:
        with RUN_LOCK:
            LAST_RUN = {"status": "error", "ts": store.utc_now_iso(), "message": str(e)}


@app.get("/")
def index():
    incidents = store.list_incidents(limit=50)
    events = store.read_events(limit=50)
    with RUN_LOCK:
        lr = dict(LAST_RUN)
    return render_template("index.html", app_name=APP_NAME, last_run=lr, incidents=incidents, events=events)


@app.get("/scenarios")
def scenarios():
    return render_template("scenarios.html", app_name=APP_NAME, scenarios=SCENARIOS, defaults=config["simulation"])


@app.get("/run/<name>")
def run_scenario(name: str):
    params: Dict[str, Any] = {}
    if name == "auth_burst":
        d = config["simulation"]["auth_burst"]
        params = {
            "user": request.args.get("user", d["user"]),
            "ip": request.args.get("ip", d["ip"]),
            "count": int(request.args.get("count", d["count"])),
            "delay_s": float(request.args.get("delay_s", d["delay_s"])),
        }
    elif name == "beacon":
        d = config["simulation"]["beacon"]
        params = {
            "host": request.args.get("host", d["host"]),
            "interval_s": float(request.args.get("interval_s", d["interval_s"])),
            "cycles": int(request.args.get("cycles", d["cycles"])),
        }

    t = threading.Thread(target=run_scenario_and_detect, args=(name, params), daemon=True)
    t.start()
    return redirect(url_for("index"))


@app.get("/incidents")
def incidents():
    incidents = store.list_incidents(limit=200)
    return render_template("incidents.html", app_name=APP_NAME, incidents=incidents)


@app.get("/incident/<inc_id>")
def incident_detail(inc_id: str):
    inc = store.get_incident(inc_id)
    if not inc:
        return "Incident not found", 404
    return render_template("incident_detail.html", app_name=APP_NAME, incident=inc)


@app.get("/playbook/<inc_id>/<name>")
def run_playbook(inc_id: str, name: str):
    ok = orchestrator.run_playbook(inc_id=inc_id, playbook_name=name, artifacts_dir=ARTIFACTS_DIR)
    if not ok:
        return "Playbook or incident not found", 404
    return redirect(url_for("incident_detail", inc_id=inc_id))


@app.get("/events")
def events():
    events = store.read_events(limit=200)
    return render_template("events.html", app_name=APP_NAME, events=events, events_file=str(EVENTS_FILE))


@app.get("/api/status")
def api_status():
    with RUN_LOCK:
        return jsonify(LAST_RUN)


@app.post("/api/detect")
def api_detect():
    detections = detector.detect_once()
    created = detector.create_incidents_from_detections(detections)
    return jsonify({"detections": detections, "created_incidents": created})


if __name__ == "__main__":
    app.run(host=config["app"]["host"], port=int(config["app"]["port"]), debug=True)
