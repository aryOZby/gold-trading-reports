from __future__ import annotations

import base64
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path

from .config import EmailConfig
from .google_auth import GMAIL_SCOPE, load_credentials
from .report import Summary

_XLSX = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def summary_html(month_label: str, rows: list[tuple[str, Summary]], drive_link: str = "") -> str:
    head = "".join(
        f"<th style='padding:4px 8px;background:#1F3864;color:#fff'>{h}</th>"
        for h in ("Group", "Trades", "Profit", "Loss", "Breakeven", "Not executed", "Open", "Win rate", "Net profit $")
    )
    body = ""
    for name, s in rows:
        rate = f"{s.win_rate:.0%}" if s.win_rate is not None else "—"
        color = "#006100" if s.profit > 0 else "#9C0006" if s.profit < 0 else "#000"
        cells = [escape(name), s.trades, s.wins, s.losses, s.breakeven, s.not_executed, s.open, rate]
        body += "<tr>" + "".join(f"<td style='padding:4px 8px;border:1px solid #ddd'>{c}</td>" for c in cells)
        body += f"<td style='padding:4px 8px;border:1px solid #ddd;color:{color}'>{s.profit:,.2f}</td></tr>"
    drive = f"<p>The same files are in Google Drive: <a href='{escape(drive_link)}'>{escape(month_label)}</a>.</p>" if drive_link else ""
    return (
        f"<p>Gold Trading — monthly report for <b>{escape(month_label)}</b> (Israel time).</p>"
        f"<table style='border-collapse:collapse;font-family:Arial;font-size:13px'><tr>{head}</tr>{body}</table>"
        "<p>One Excel file per group is attached: <i>Trades</i> (one row per signal, N numbering), "
        "<i>Positions</i> (every position or order of each signal), and <i>Summary</i> (totals and per strategy).</p>"
        f"{drive}"
    )


def build_message(cfg: EmailConfig, subject: str, html: str, attachments: list[Path]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    if cfg.sender:
        msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.to)
    msg.set_content("This report is best viewed in an HTML-capable mail client. The Excel files are attached.")
    msg.add_alternative(html, subtype="html")
    for path in attachments:
        msg.add_attachment(path.read_bytes(), maintype=_XLSX[0], subtype=_XLSX[1], filename=path.name)
    return msg


def send(cfg: EmailConfig, msg: EmailMessage, token_path: Path) -> None:
    if not cfg.to:
        raise ValueError("email.to is empty in config.yaml")
    if cfg.method == "gmail_api":
        send_gmail_api(msg, token_path)
    else:
        send_smtp(cfg, msg)


def send_gmail_api(msg: EmailMessage, token_path: Path) -> None:
    """Send as the signed-in Google account; no App Password needed."""
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=load_credentials(token_path, GMAIL_SCOPE), cache_discovery=False)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_smtp(cfg: EmailConfig, msg: EmailMessage) -> None:
    if not cfg.username or not cfg.password:
        raise ValueError("email.username in config.yaml and SMTP_PASSWORD in .env are required")
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(cfg.username, cfg.password)
        smtp.send_message(msg)
