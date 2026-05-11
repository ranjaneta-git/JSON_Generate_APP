"""Export generated configs to JSON files and project save/load."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(data: dict[str, Any], path: str | Path) -> None:
    """Write a config dict to a JSON file (compact, no trailing whitespace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def write_json_pretty(data: dict[str, Any], path: str | Path) -> None:
    """Write a config dict to a JSON file (human-readable)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
