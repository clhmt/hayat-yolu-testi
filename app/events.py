import json
from pathlib import Path
from datetime import datetime

def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def log_event(path: Path, name: str, payload: dict) -> None:
    event = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event": name,
        **(payload or {}),
    }
    append_event(path, event)
