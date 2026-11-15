from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool
    method: str
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    sender: str
    to: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GoogleConfig:
    client_file: Path
    token_file: Path


@dataclass(frozen=True)
class DriveConfig:
    enabled: bool
    folder: str


@dataclass(frozen=True)
class AppConfig:
    tz: ZoneInfo
    journal_dir: Path
    reports_dir: Path
    data_dir: Path
    logs_dir: Path
    breakeven_tolerance: float
    friday_close: time
    groups: dict[int, str]
    email: EmailConfig
    drive: DriveConfig
    google: GoogleConfig

    def group_name(self, slot: int) -> str:
        return self.groups.get(slot, f"Group {slot}")


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv(ROOT / ".env")
    path = path or ROOT / "config.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    hh, mm = str(raw.get("friday_close") or "23:30").split(":")
    mail = raw.get("email") or {}
    username = str(mail.get("username") or "")
    to = mail.get("to") or []
    if isinstance(to, str):
        to = [to]
    drive = raw.get("drive") or {}
    google = raw.get("google") or {}
    method = str(mail.get("method") or "gmail_api")
    if method not in ("gmail_api", "smtp"):
        raise ValueError(f"email.method must be gmail_api or smtp, got {method}")
    return AppConfig(
        tz=ZoneInfo(str(raw.get("timezone") or "Asia/Jerusalem")),
        journal_dir=_resolve(str(raw.get("journal_dir") or "journal")),
        reports_dir=_resolve(str(raw.get("reports_dir") or "reports")),
        data_dir=ROOT / "data",
        logs_dir=ROOT / "logs",
        breakeven_tolerance=float(raw.get("breakeven_tolerance", 0.1)),
        friday_close=time(int(hh), int(mm)),
        groups={int(k): str(v) for k, v in (raw.get("groups") or {}).items()},
        email=EmailConfig(
            enabled=bool(mail.get("enabled", False)),
            method=method,
            smtp_host=str(mail.get("smtp_host") or "smtp.gmail.com"),
            smtp_port=int(mail.get("smtp_port") or 587),
            username=username,
            password=os.getenv("SMTP_PASSWORD", ""),
            sender=str(mail.get("sender") or username),
            to=[str(x) for x in to],
        ),
        drive=DriveConfig(
            enabled=bool(drive.get("enabled", False)),
            folder=str(drive.get("folder") or "Gold Trading Reports"),
        ),
        google=GoogleConfig(
            client_file=_resolve(str(google.get("client_file") or "secrets/google_client.json")),
            token_file=_resolve(str(google.get("token_file") or "secrets/google_token.json")),
        ),
    )
