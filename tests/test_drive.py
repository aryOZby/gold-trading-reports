import re
from pathlib import Path

from src.drive import FOLDER_MIME, upload_month


class _Call:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class FakeFiles:
    """In-memory stand-in for service.files() with the subset of Drive v3 we use."""

    def __init__(self):
        self.items: dict[str, dict] = {}
        self.updates: list[str] = []

    def list(self, q, **_):
        name = re.search(r"name = '((?:[^'\\]|\\.)*)'", q).group(1).replace("\\'", "'")
        parent = re.search(r"'([^']+)' in parents", q).group(1)
        folder_only = FOLDER_MIME in q
        hits = [
            {"id": i, "webViewLink": f"https://drive/{i}"}
            for i, f in self.items.items()
            if f["name"] == name and parent in f["parents"] and (not folder_only or f.get("mimeType") == FOLDER_MIME)
        ]
        return _Call({"files": hits[:1]})

    def create(self, body, media_body=None, **_):
        new_id = f"id{len(self.items) + 1}"
        self.items[new_id] = dict(body)
        return _Call({"id": new_id, "webViewLink": f"https://drive/{new_id}"})

    def update(self, fileId, media_body, **_):
        self.updates.append(fileId)
        return _Call({"id": fileId})


class FakeService:
    def __init__(self):
        self._files = FakeFiles()

    def files(self):
        return self._files


def test_upload_creates_folders_once_and_replaces_files(tmp_path: Path):
    a = tmp_path / "2026-11 G1 VIP.xlsx"
    b = tmp_path / "2026-11 G2 Technical Pips.xlsx"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    service = FakeService()

    link = upload_month(service, "Gold Trading Reports", "2026-11", [a, b])
    items = service.files().items
    folders = {f["name"]: i for i, f in items.items() if f.get("mimeType") == FOLDER_MIME}
    assert set(folders) == {"Gold Trading Reports", "2026-11"}
    assert items[folders["Gold Trading Reports"]]["parents"] == ["root"]
    assert items[folders["2026-11"]]["parents"] == [folders["Gold Trading Reports"]]
    assert link == f"https://drive/{folders['2026-11']}"
    assert len(items) == 4

    upload_month(service, "Gold Trading Reports", "2026-11", [a, b])
    assert len(items) == 4
    assert len(service.files().updates) == 2
