"""One-time Google Drive sign-in on the server.

Put the OAuth client downloaded from Google Cloud in secrets\\drive_client.json, run this,
sign in with the Google account that should hold the reports, and allow access. The token
is saved to secrets\\drive_token.json and refreshed automatically afterwards.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from src.config import load_config  # noqa: E402
from src.drive import SCOPES, build_service, ensure_folder  # noqa: E402


def main() -> int:
    cfg = load_config()
    client = cfg.drive.client_file
    if not client.exists():
        print(f"Missing {client}. Download the OAuth client (Desktop app) JSON from Google Cloud and save it there.")
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    cfg.drive.token_file.parent.mkdir(parents=True, exist_ok=True)
    cfg.drive.token_file.write_text(creds.to_json(), encoding="utf-8")
    folder = ensure_folder(build_service(cfg.drive.token_file), cfg.drive.folder)
    print(f"Drive connected. Reports folder: {folder.get('webViewLink', cfg.drive.folder)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
