
# app/storage.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -------------------------
# Models
# -------------------------
@dataclass(frozen=True)
class JsonlReadReport:
    records: List[Dict[str, Any]]
    bad_lines: int


# -------------------------
# Path helpers
# -------------------------
def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# -------------------------
# JSONL read/write (robust)
# -------------------------
def read_jsonl(path: Path) -> JsonlReadReport:
    """
    Robust JSONL reader.
    - Skips empty lines
    - Skips invalid JSON lines (counts as bad_lines)
    - Skips non-dict JSON payloads (counts as bad_lines)

    Returns:
      JsonlReadReport(records=[...], bad_lines=N)
    """
    if not path.exists():
        return JsonlReadReport(records=[], bad_lines=0)

    records: List[Dict[str, Any]] = []
    bad = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    bad += 1
            except json.JSONDecodeError:
                bad += 1

    return JsonlReadReport(records=records, bad_lines=bad)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """
    Append a single dict record as JSON line.
    """
    ensure_parent_dir(path)
    line = json.dumps(record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()


# -------------------------
# Lookup / Index helpers
# -------------------------
def build_index_by_profile_id(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Builds {profile_id: record}. If duplicates exist, the last seen wins.
    """
    idx: Dict[str, Dict[str, Any]] = {}
    for r in records:
        pid = r.get("profile_id")
        if isinstance(pid, str) and pid:
            idx[pid] = r
    return idx


def find_by_profile_id(path: Path, profile_id: str) -> Optional[Dict[str, Any]]:
    """
    Finds a record by profile_id by scanning the file.
    - Robust to bad lines.
    - Returns the *last* match if duplicates exist.
    """
    if not profile_id or not isinstance(profile_id, str):
        return None
    if not path.exists():
        return None

    found: Optional[Dict[str, Any]] = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("profile_id") == profile_id:
                found = obj
    return found


def profile_id_exists(path: Path, profile_id: str) -> bool:
    return find_by_profile_id(path, profile_id) is not None


def ensure_unique_profile_id(path: Path, requested_id: Optional[str] = None) -> str:
    """
    Ensures we return a profile_id that doesn't already exist in the log.
    If requested_id is None/empty -> generate.
    If requested_id exists -> generate a new one.
    """
    candidate = requested_id if (isinstance(requested_id, str) and requested_id.strip()) else str(uuid.uuid4())
    candidate = candidate.strip()

    # Avoid collisions with existing file content
    if profile_id_exists(path, candidate):
        return str(uuid.uuid4())
    return candidate


def append_unique_by_profile_id(path: Path, record: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Writes record only if its profile_id does not already exist in the log.

    Returns:
      (written: bool, profile_id: str)

    Behavior:
      - If record has no profile_id -> generate unique, write.
      - If record has profile_id but exists -> do not write (written=False).
      - If record has profile_id and doesn't exist -> write (written=True).
    """
    pid = record.get("profile_id")
    if not isinstance(pid, str) or not pid.strip():
        pid = ensure_unique_profile_id(path, None)
        record["profile_id"] = pid
        append_jsonl(path, record)
        return True, pid

    pid = pid.strip()
    record["profile_id"] = pid

    if profile_id_exists(path, pid):
        return False, pid

    append_jsonl(path, record)
    return True, pid

import json
from datetime import datetime
from pathlib import Path

def log_event(path: Path, event: dict) -> None:
    """
    Append-only JSONL event logger.
    """
    event = dict(event)
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

