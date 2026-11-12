from datetime import datetime, time
from pathlib import Path

from openpyxl import load_workbook

from src.excel import workbook_path, write_group_workbook
from src.journal import parse_tag, read_journal
from src.report import BREAKEVEN, LOSS, NOT_EXECUTED, OPEN, PROFIT, build_month, summarize
from src.schedule import already_sent, mark_sent, previous_month

FRIDAY = time(23, 30)


def _november(journal_dir: Path):
    return build_month(read_journal(journal_dir), 2026, 11, 0.1, FRIDAY)


def test_comment_tag():
    tag = parse_tag("S3|G4|N12|tp5")
    assert (tag.strategy, tag.group, tag.number, tag.tp_row) == (3, 4, 12, 5)
    assert parse_tag("GT1-18857-TP4") is None


def test_older_rows_without_tag_are_ignored(journal_dir: Path):
    assert read_journal(journal_dir).untagged == 1


def test_trade_is_one_signal_numbered_per_group(journal_dir: Path):
    groups = _november(journal_dir)
    assert [t.number for t in groups[2]] == [1, 2, 3]
    assert [t.number for t in groups[4]] == [1, 2]
    n1 = groups[2][0]
    assert n1.strategy == 1 and n1.side == "SELL" and len(n1.legs) == 3
    assert n1.placed == datetime(2026, 11, 3, 10, 0)
    assert n1.closed == datetime(2026, 11, 3, 12, 0)


def test_breakeven_legs_and_profit(journal_dir: Path):
    n1 = _november(journal_dir)[2][0]
    assert [leg.outcome for leg in n1.legs] == ["TP", BREAKEVEN, BREAKEVEN]
    assert n1.tp_hits == 1
    assert n1.result == PROFIT
    assert n1.profit == round(15.00 - 0.07 - 0.12 - 0.12, 2)


def test_full_stop_is_a_loss(journal_dir: Path):
    n2 = _november(journal_dir)[2][1]
    assert [leg.outcome for leg in n2.legs] == ["SL", "SL", "SL"]
    assert n2.result == LOSS


def test_friday_close_is_named(journal_dir: Path):
    n3 = _november(journal_dir)[2][2]
    assert n3.legs[0].outcome == "Friday close"
    assert n3.strategy == 2


def test_not_executed_and_open(journal_dir: Path):
    g4 = _november(journal_dir)[4]
    assert g4[0].result == NOT_EXECUTED
    assert g4[0].legs[0].outcome == "Not executed — TP1 reached first"
    assert g4[0].closed is None
    assert g4[1].result == OPEN


def test_month_follows_placement(journal_dir: Path):
    assert 1 not in _november(journal_dir)
    october = build_month(read_journal(journal_dir), 2026, 10, 0.1, FRIDAY)
    assert [t.number for t in october[1]] == [1]


def test_summary_counts(journal_dir: Path):
    s = summarize(_november(journal_dir)[2])
    assert (s.trades, s.wins, s.losses, s.executed) == (3, 2, 1, 3)
    assert abs(s.win_rate - 2 / 3) < 1e-9


def test_workbook_per_group(journal_dir: Path, tmp_path: Path):
    trades = _november(journal_dir)[2]
    path = workbook_path(tmp_path / "out", 2, "Technical Pips ™", 2026, 11)
    write_group_workbook(path, 2, "Technical Pips ™", 2026, 11, trades, datetime(2026, 12, 1, 9, 0))
    assert path.name == "2026-11 G2 Technical Pips.xlsx"
    wb = load_workbook(path)
    assert wb.sheetnames == ["Trades", "Positions", "Summary"]
    rows = list(wb["Trades"].iter_rows(values_only=True))
    assert rows[0][:3] == ("N", "Strategy", "Side")
    assert [r[0] for r in rows[1:]] == ["N1", "N2", "N3"]
    assert rows[1][11] == PROFIT
    assert wb["Positions"].max_row == 1 + 3 + 3 + 1


def test_previous_month_and_sent_once(tmp_path: Path):
    assert previous_month(datetime(2027, 1, 1)) == (2026, 12)
    assert previous_month(datetime(2026, 12, 1)) == (2026, 11)
    assert not already_sent(tmp_path, "2026-11")
    mark_sent(tmp_path, "2026-11", datetime(2026, 12, 1, 9, 0))
    assert already_sent(tmp_path, "2026-11")
