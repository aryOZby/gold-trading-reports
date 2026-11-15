"""Monthly per-group Excel report of the Chart Executor's trades, emailed and uploaded to Google Drive.

Run daily (scripts/install-task.ps1). On the first run of a new month it delivers the previous
month once; a failed email or upload is retried on the next run. Use --month to rebuild or
resend any month.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from src.config import load_config
from src.drive import build_service, upload_month
from src.excel import workbook_path, write_group_workbook
from src.journal import read_journal
from src.mailer import build_message, send, summary_html
from src.report import build_month, summarize
from src.schedule import is_done, mark_done, month_label, parse_month, previous_month

_LOG = logging.getLogger("reports")


def setup_logging(logs_dir) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(logs_dir / "reports.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    if sys.stdout is not None:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        root.addHandler(console)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", help="YYYY-MM to report (default: previous month, once)")
    parser.add_argument("--no-email", action="store_true", help="do not send the email")
    parser.add_argument("--no-drive", action="store_true", help="do not upload to Google Drive")
    args = parser.parse_args(argv)

    cfg = load_config()
    setup_logging(cfg.logs_dir)
    now = datetime.now(cfg.tz).replace(tzinfo=None)
    year, month = parse_month(args.month) if args.month else previous_month(now)
    label = month_label(year, month)
    scheduled = args.month is None
    do_email = cfg.email.enabled and not args.no_email
    do_drive = cfg.drive.enabled and not args.no_drive
    if scheduled:
        pending = [s for s, on in (("email", do_email), ("drive", do_drive)) if on and not is_done(cfg.data_dir, label, s)]
        if not pending:
            _LOG.info("Report %s already delivered — nothing to do", label)
            return 0
        do_email = "email" in pending

    journal = read_journal(cfg.journal_dir)
    if journal.untagged:
        _LOG.info("Ignored %d journal rows without an S|G|N|tp comment (older trades)", journal.untagged)
    by_group = build_month(journal, year, month, cfg.breakeven_tolerance, cfg.friday_close)

    files = []
    rows = []
    for group in sorted(set(cfg.groups) | set(by_group)):
        trades = by_group.get(group, [])
        name = cfg.group_name(group)
        path = write_group_workbook(
            workbook_path(cfg.reports_dir, group, name, year, month), group, name, year, month, trades, now
        )
        files.append(path)
        s = summarize(trades)
        rows.append((f"G{group} {name}", s))
        _LOG.info(
            "%s G%d %s: %d trades, %d profit, %d loss, %d breakeven, %d not executed, %d open, net %.2f -> %s",
            label, group, name, s.trades, s.wins, s.losses, s.breakeven, s.not_executed, s.open, s.profit, path,
        )

    failed = False
    drive_link = ""
    if do_drive:
        try:
            drive_link = upload_month(build_service(cfg.google.token_file), cfg.drive.folder, label, files)
            _LOG.info("Report %s uploaded to Google Drive: %s", label, drive_link)
            if scheduled:
                mark_done(cfg.data_dir, label, "drive", now)
        except Exception:
            _LOG.exception("Google Drive upload failed")
            failed = True

    if do_email:
        try:
            html = summary_html(label, rows, drive_link)
            msg = build_message(cfg.email, f"Gold Trading — monthly report {label}", html, files)
            send(cfg.email, msg, cfg.google.token_file)
            _LOG.info("Report %s emailed to %s", label, ", ".join(cfg.email.to))
            if scheduled:
                mark_done(cfg.data_dir, label, "email", now)
        except Exception:
            _LOG.exception("Email failed")
            failed = True

    _LOG.info("Files are in %s", cfg.reports_dir / label)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _LOG.exception("Report failed")
        raise
