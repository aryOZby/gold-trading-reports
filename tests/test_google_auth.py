import json
from pathlib import Path

import pytest

from src.google_auth import DRIVE_SCOPE, GMAIL_SCOPE, load_credentials


def test_missing_token_asks_for_sign_in(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="authorize_google"):
        load_credentials(tmp_path / "google_token.json", GMAIL_SCOPE)


def test_scope_not_granted_asks_for_sign_in_again(tmp_path: Path):
    token = tmp_path / "google_token.json"
    token.write_text(json.dumps({"scopes": [DRIVE_SCOPE], "refresh_token": "r"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="gmail.send"):
        load_credentials(token, GMAIL_SCOPE)
