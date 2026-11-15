"""One-time Google sign-in on the server, for the Drive upload and the Gmail sender.

Put the OAuth client downloaded from Google Cloud in secrets\\google_client.json, run this,
sign in with the Google account that sends and keeps the reports, and allow both permissions.
The token is saved to secrets\\google_token.json and refreshed automatically afterwards.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from src.config import load_config  # noqa: E402
from src.drive import build_service, ensure_folder  # noqa: E402
from src.google_auth import DRIVE_SCOPE, GMAIL_SCOPE, SCOPES  # noqa: E402


def main() -> int:
    cfg = load_config()
    client = cfg.google.client_file
    if not client.exists():
        print(f"Missing {client}. Download the OAuth client (Desktop app) JSON from Google Cloud and save it there.")
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    granted = list(getattr(creds, "granted_scopes", None) or creds.scopes or [])
    token = json.loads(creds.to_json())
    token["scopes"] = granted
    cfg.google.token_file.parent.mkdir(parents=True, exist_ok=True)
    cfg.google.token_file.write_text(json.dumps(token), encoding="utf-8")

    missing = {DRIVE_SCOPE: "Google Drive", GMAIL_SCOPE: "sending email"}
    for scope, what in missing.items():
        print(f"{what}: {'allowed' if scope in granted else 'NOT allowed — run again and tick it'}")
    if DRIVE_SCOPE in granted:
        folder = ensure_folder(build_service(cfg.google.token_file), cfg.drive.folder)
        print(f"Reports folder: {folder.get('webViewLink', cfg.drive.folder)}")
    return 0 if all(s in granted for s in SCOPES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
