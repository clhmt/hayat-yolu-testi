from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def project_root() -> Path:
    """
    Returns the repository root path.
    Assumes this file lives in: repo/app/utils.py
    """
    return Path(__file__).resolve().parents[1]


def data_path(filename: str) -> Path:
    """
    Convenience helper to locate files under /data.
    Example: data_path("questions.json")
    """
    return project_root() / "data" / filename


def load_json(filename: str) -> Dict[str, Any]:
    """
    Loads a JSON file from /data and returns it as a dict.
    """
    path = data_path(filename)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
