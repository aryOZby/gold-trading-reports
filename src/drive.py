"""Upload the monthly workbooks to Google Drive: <folder>/<YYYY-MM>/<file>.xlsx.

Uses the drive.file scope: the app only sees the folders and files it created itself.
"""

from __future__ import annotations

from pathlib import Path

from .google_auth import DRIVE_SCOPE, load_credentials

FOLDER_MIME = "application/vnd.google-apps.folder"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_service(token_path: Path):
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=load_credentials(token_path, DRIVE_SCOPE), cache_discovery=False)


def _quoted(name: str) -> str:
    return name.replace("\\", "\\\\").replace("'", "\\'")


def _find(service, name: str, parent: str, mime: str | None = None) -> dict | None:
    query = f"name = '{_quoted(name)}' and '{parent}' in parents and trashed = false"
    if mime:
        query += f" and mimeType = '{mime}'"
    found = service.files().list(q=query, spaces="drive", fields="files(id, webViewLink)", pageSize=1).execute()
    files = found.get("files", [])
    return files[0] if files else None


def ensure_folder(service, name: str, parent: str = "root") -> dict:
    existing = _find(service, name, parent, FOLDER_MIME)
    if existing:
        return existing
    body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
    return service.files().create(body=body, fields="id, webViewLink").execute()


def upload_month(service, root_folder: str, label: str, files: list[Path]) -> str:
    """Create or replace every file in <root_folder>/<label>; returns the month folder link."""
    from googleapiclient.http import MediaFileUpload

    root = ensure_folder(service, root_folder)
    month = ensure_folder(service, label, root["id"])
    for path in files:
        media = MediaFileUpload(str(path), mimetype=XLSX_MIME, resumable=False)
        existing = _find(service, path.name, month["id"])
        if existing:
            service.files().update(fileId=existing["id"], media_body=media).execute()
        else:
            body = {"name": path.name, "parents": [month["id"]]}
            service.files().create(body=body, media_body=media, fields="id").execute()
    return month.get("webViewLink", "")
