from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

SENT_FILE = "sent.json"


def previous_month(now: datetime) -> tuple[int, int]:
    if now.month == 1:
        return now.year - 1, 12
    return now.year, now.month - 1


def parse_month(text: str) -> tuple[int, int]:
    year, month = text.split("-")
    y, m = int(year), int(month)
    if not 1 <= m <= 12:
        raise ValueError(f"month must be YYYY-MM, got {text}")
    return y, m


def month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _load(data_dir: Path) -> dict[str, str]:
    path = data_dir / SENT_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def already_sent(data_dir: Path, label: str) -> bool:
    return label in _load(data_dir)


def mark_sent(data_dir: Path, label: str, when: datetime) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    sent = _load(data_dir)
    sent[label] = when.isoformat(timespec="seconds")
    tmp = data_dir / (SENT_FILE + ".tmp")
    tmp.write_text(json.dumps(sent, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, data_dir / SENT_FILE)
