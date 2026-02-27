# IR Simulation Tool (MVP)

Bezpečný nástroj pro simulaci incidentů: scénáře generují události (JSONL), detekční engine z nich dělá incidenty a playbooky přidávají response akce.

## Instalace
```bash
cd ir_sim
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

## Spuštění
```bash
python app.py
```
Otevři: http://127.0.0.1:5000

## Data
- data/events.jsonl (události)
- data/incidents.jsonl (incidenty)
- data/artifacts/<incident_id>/evidence.json (artifacty z playbooku)
