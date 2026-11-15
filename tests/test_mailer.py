from pathlib import Path

from src.config import EmailConfig
from src.mailer import build_message, summary_html
from src.report import Summary


def test_message_has_html_summary_and_attachments(tmp_path: Path):
    xlsx = tmp_path / "2026-11 G2 Technical Pips.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")
    cfg = EmailConfig(True, "gmail_api", "smtp.gmail.com", 587, "", "", "", ["me@example.com"])
    html = summary_html("2026-11", [("G2 Technical Pips", Summary(3, 3, 0, 0, 2, 1, 0, 12.5))])
    msg = build_message(cfg, "Gold Trading — monthly report 2026-11", html, [xlsx])
    assert msg["To"] == "me@example.com"
    assert msg["From"] is None
    names = [part.get_filename() for part in msg.iter_attachments()]
    assert names == ["2026-11 G2 Technical Pips.xlsx"]
    assert "67%" in html and "12.50" in html
