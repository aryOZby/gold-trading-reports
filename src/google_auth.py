"""One Google sign-in shared by the Drive upload and the Gmail API sender."""

from __future__ import annotations

import json
from pathlib import Path

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SCOPES = [DRIVE_SCOPE, GMAIL_SCOPE]

_REAUTHORIZE = "run scripts\\authorize_google.py"


def load_credentials(token_path: Path, scope: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not token_path.exists():
        raise FileNotFoundError(f"{token_path} is missing — {_REAUTHORIZE} once")
    granted = json.loads(token_path.read_text(encoding="utf-8")).get("scopes") or []
    if scope not in granted:
        raise PermissionError(f"Google sign-in does not allow {scope} — {_REAUTHORIZE} again")
    creds = Credentials.from_authorized_user_file(str(token_path), granted)
    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError(f"Google token cannot be refreshed — {_REAUTHORIZE} again")
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
