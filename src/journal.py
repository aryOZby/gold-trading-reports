"""Readers for the CSV journal the Chart Executor EA keeps in MT5 Common\\Files\\gt_journal."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CLOSED_FILE = "closed.csv"
OPEN_FILE = "open.csv"
UNFILLED_FILE = "unfilled.csv"

# Order comment set by the EA: S<strategy>|G<group>|N<monthly number>|tp<TP row>
_TAG = re.compile(r"^S(?P<s>\d+)\|G(?P<g>\d+)\|N(?P<n>\d+)\|tp(?P<tp>\d+)$")


@dataclass(frozen=True)
class Tag:
    strategy: int
    group: int
    number: int
    tp_row: int


def parse_tag(comment: str) -> Tag | None:
    m = _TAG.match(comment.strip())
    if m is None:
        return None
    return Tag(int(m["s"]), int(m["g"]), int(m["n"]), int(m["tp"]))


def parse_time(text: str) -> datetime | None:
    """EA times are Israel wall-clock 'YYYY.MM.DD HH:MM:SS'."""
    text = (text or "").strip()
    if not text:
        return None
    return datetime.strptime(text, "%Y.%m.%d %H:%M:%S")


def _float(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class ClosedDeal:
    deal: int
    position: int
    tag: Tag
    side: str
    lot: float
    placed: datetime
    opened: datetime
    closed: datetime
    open_price: float
    close_price: float
    initial_sl: float
    initial_tp: float
    sl_at_close: float
    net_profit: float
    reason: str


@dataclass(frozen=True)
class OpenItem:
    kind: str  # "position" or "order"
    ticket: int
    tag: Tag
    side: str
    lot: float
    placed: datetime
    opened: datetime | None
    open_price: float
    sl: float
    tp: float
    profit: float


@dataclass(frozen=True)
class UnfilledOrder:
    ticket: int
    tag: Tag
    side: str
    lot: float
    placed: datetime
    deleted: datetime
    entry: float
    sl: float
    tp: float
    reason: str


@dataclass
class Journal:
    closed: list[ClosedDeal]
    open: list[OpenItem]
    unfilled: list[UnfilledOrder]
    untagged: int = 0  # rows from before the S|G|N|tp comment format


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        return [row for row in csv.DictReader(f) if row]


def _side_from_type(order_type: str) -> str:
    return "BUY" if order_type.upper().startswith("BUY") else "SELL"


def read_journal(journal_dir: Path) -> Journal:
    journal = Journal(closed=[], open=[], unfilled=[])
    seen: set[int] = set()
    for row in _rows(journal_dir / CLOSED_FILE):
        tag = parse_tag(row.get("comment", ""))
        deal = int(row.get("deal") or 0)
        if tag is None:
            journal.untagged += 1
            continue
        if deal in seen:
            continue
        seen.add(deal)
        journal.closed.append(
            ClosedDeal(
                deal=deal,
                position=int(row["position"]),
                tag=tag,
                side=row["side"],
                lot=_float(row["lot"]),
                placed=parse_time(row["placed_israel"]) or parse_time(row["opened_israel"]),
                opened=parse_time(row["opened_israel"]),
                closed=parse_time(row["closed_israel"]),
                open_price=_float(row["open_price"]),
                close_price=_float(row["close_price"]),
                initial_sl=_float(row["initial_sl"]),
                initial_tp=_float(row["initial_tp"]),
                sl_at_close=_float(row["sl_at_close"]),
                net_profit=_float(row["profit"]) + _float(row["commission"]) + _float(row["swap"]),
                reason=row["reason"].strip(),
            )
        )
    for row in _rows(journal_dir / OPEN_FILE):
        tag = parse_tag(row.get("comment", ""))
        if tag is None:
            journal.untagged += 1
            continue
        journal.open.append(
            OpenItem(
                kind=row["kind"],
                ticket=int(row["ticket"]),
                tag=tag,
                side=row["side"],
                lot=_float(row["lot"]),
                placed=parse_time(row["placed_israel"]) or parse_time(row["opened_israel"]),
                opened=parse_time(row["opened_israel"]),
                open_price=_float(row["open_price"]),
                sl=_float(row["sl"]),
                tp=_float(row["tp"]),
                profit=_float(row["profit"]),
            )
        )
    for row in _rows(journal_dir / UNFILLED_FILE):
        tag = parse_tag(row.get("comment", ""))
        if tag is None:
            journal.untagged += 1
            continue
        journal.unfilled.append(
            UnfilledOrder(
                ticket=int(row["ticket"]),
                tag=tag,
                side=_side_from_type(row["type"]),
                lot=_float(row["lot"]),
                placed=parse_time(row["placed_israel"]),
                deleted=parse_time(row["deleted_israel"]),
                entry=_float(row["entry"]),
                sl=_float(row["sl"]),
                tp=_float(row["tp"]),
                reason=row["reason"].strip(),
            )
        )
    return journal
