from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .report import BREAKEVEN, LOSS, NOT_EXECUTED, OPEN, PROFIT, Trade, summarize

_HEADER_FILL = PatternFill("solid", fgColor="1F3864")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_RESULT_FILL = {
    PROFIT: PatternFill("solid", fgColor="C6EFCE"),
    LOSS: PatternFill("solid", fgColor="FFC7CE"),
    BREAKEVEN: PatternFill("solid", fgColor="FFEB9C"),
    OPEN: PatternFill("solid", fgColor="DDEBF7"),
    NOT_EXECUTED: PatternFill("solid", fgColor="E7E6E6"),
}
_DT = "yyyy-mm-dd hh:mm"
_MONEY = '#,##0.00;[Red]-#,##0.00'
_PRICE = "0.00"

TRADE_COLUMNS = [
    "N", "Strategy", "Side", "Placed", "Opened", "Closed", "Positions", "Lot",
    "Entry", "SL", "TPs hit", "Result", "Net profit $", "Positions detail",
]
LEG_COLUMNS = [
    "N", "Strategy", "TP row", "Side", "Lot", "Placed", "Opened", "Closed",
    "Entry", "Exit", "SL", "TP", "Outcome", "Net profit $",
]


def _safe_name(text: str) -> str:
    return re.sub(r"[^\w\- ()]+", "", text).strip() or "Group"


def _header(ws, columns: list[str]) -> None:
    ws.append(columns)
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"


def _widths(ws, widths: dict[int, int]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def _format(ws, row: int, formats: dict[int, str]) -> None:
    for col, fmt in formats.items():
        ws.cell(row=row, column=col).number_format = fmt


def write_group_workbook(
    path: Path,
    group: int,
    group_name: str,
    year: int,
    month: int,
    trades: list[Trade],
    generated: datetime,
) -> Path:
    wb = Workbook()

    ws = wb.active
    ws.title = "Trades"
    _header(ws, TRADE_COLUMNS)
    for t in trades:
        ws.append([
            f"N{t.number}", f"S{t.strategy}", t.side, t.placed, t.opened, t.closed, len(t.legs), t.lot,
            t.entry, t.sl, t.tp_hits, t.result, t.profit, t.outcomes,
        ])
        r = ws.max_row
        _format(ws, r, {4: _DT, 5: _DT, 6: _DT, 9: _PRICE, 10: _PRICE, 13: _MONEY})
        ws.cell(row=r, column=12).fill = _RESULT_FILL.get(t.result, PatternFill())
    _widths(ws, {1: 7, 2: 9, 3: 7, 4: 17, 5: 17, 6: 17, 7: 10, 8: 7, 9: 10, 10: 10, 11: 8, 12: 14, 13: 13, 14: 60})

    legs = wb.create_sheet("Positions")
    _header(legs, LEG_COLUMNS)
    for t in trades:
        for leg in t.legs:
            legs.append([
                f"N{t.number}", f"S{t.strategy}", f"TP{leg.tp_row}", leg.side, leg.lot, leg.placed,
                leg.opened, leg.closed, leg.entry, leg.exit, leg.sl, leg.tp, leg.outcome, leg.profit,
            ])
            _format(legs, legs.max_row, {6: _DT, 7: _DT, 8: _DT, 9: _PRICE, 10: _PRICE, 11: _PRICE, 12: _PRICE, 14: _MONEY})
    _widths(legs, {1: 7, 2: 9, 3: 8, 4: 7, 5: 7, 6: 17, 7: 17, 8: 17, 9: 10, 10: 10, 11: 10, 12: 10, 13: 34, 14: 13})

    summary = wb.create_sheet("Summary")
    s = summarize(trades)
    rows = [
        ("Group", f"G{group} — {group_name}"),
        ("Month", f"{year:04d}-{month:02d}"),
        ("Trades", s.trades),
        ("Executed", s.executed),
        ("Not executed", s.not_executed),
        ("Still open", s.open),
        ("Profit", s.wins),
        ("Loss", s.losses),
        ("Breakeven", s.breakeven),
        ("Win rate", s.win_rate if s.win_rate is not None else "—"),
        ("Net profit $", s.profit),
        ("Generated (Israel time)", generated),
    ]
    for label, value in rows:
        summary.append([label, value])
        summary.cell(row=summary.max_row, column=1).font = Font(bold=True)
    summary["B10"].number_format = "0.0%"
    summary["B11"].number_format = _MONEY
    summary["B12"].number_format = _DT

    summary.append([])
    start = summary.max_row + 1
    summary.append(["By strategy", "Trades", "Profit", "Loss", "Breakeven", "Not executed", "Open", "Win rate", "Net profit $"])
    for cell in summary[start]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    by_strategy: dict[int, list[Trade]] = defaultdict(list)
    for t in trades:
        by_strategy[t.strategy].append(t)
    for strategy in sorted(by_strategy):
        ss = summarize(by_strategy[strategy])
        summary.append([
            f"S{strategy}", ss.trades, ss.wins, ss.losses, ss.breakeven, ss.not_executed, ss.open,
            ss.win_rate if ss.win_rate is not None else "—", ss.profit,
        ])
        _format(summary, summary.max_row, {8: "0.0%", 9: _MONEY})
    _widths(summary, {1: 24, 2: 30, 3: 9, 4: 9, 5: 11, 6: 13, 7: 8, 8: 10, 9: 13})

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def workbook_path(reports_dir: Path, group: int, group_name: str, year: int, month: int) -> Path:
    stamp = f"{year:04d}-{month:02d}"
    return reports_dir / stamp / f"{stamp} G{group} {_safe_name(group_name)}.xlsx"
