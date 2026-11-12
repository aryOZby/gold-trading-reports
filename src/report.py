"""Turn journal rows into one trade per signal (group + monthly number) for a calendar month."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time

from .journal import ClosedDeal, Journal

PROFIT = "Profit"
LOSS = "Loss"
BREAKEVEN = "Breakeven"
OPEN = "Open"
NOT_EXECUTED = "Not executed"

_EPS = 0.005

_NOT_EXECUTED_REASONS = {
    "expired": "Not executed — expired",
    "tp1_before_fill": "Not executed — TP1 reached first",
    "breakeven": "Not executed — cancelled at breakeven",
    "friday_close": "Not executed — Friday close",
}


@dataclass
class Leg:
    tp_row: int
    side: str
    lot: float
    placed: datetime
    opened: datetime | None
    closed: datetime | None
    entry: float
    exit: float | None
    sl: float
    tp: float
    profit: float
    outcome: str


@dataclass
class Trade:
    group: int
    number: int
    strategy: int
    side: str
    legs: list[Leg] = field(default_factory=list)

    @property
    def placed(self) -> datetime:
        return min(leg.placed for leg in self.legs)

    @property
    def opened(self) -> datetime | None:
        times = [leg.opened for leg in self.legs if leg.opened]
        return min(times) if times else None

    @property
    def closed(self) -> datetime | None:
        if self.result in (OPEN, NOT_EXECUTED):
            return None
        times = [leg.closed for leg in self.legs if leg.closed]
        return max(times) if times else None

    @property
    def lot(self) -> float:
        return round(sum(leg.lot for leg in self.legs), 2)

    @property
    def entry(self) -> float:
        return self.legs[0].entry

    @property
    def sl(self) -> float:
        return self.legs[0].sl

    @property
    def profit(self) -> float:
        return round(sum(leg.profit for leg in self.legs), 2)

    @property
    def tp_hits(self) -> int:
        return sum(1 for leg in self.legs if leg.outcome == "TP")

    @property
    def result(self) -> str:
        if any(leg.outcome == OPEN for leg in self.legs):
            return OPEN
        if all(leg.outcome.startswith(NOT_EXECUTED) for leg in self.legs):
            return NOT_EXECUTED
        if self.profit > _EPS:
            return PROFIT
        if self.profit < -_EPS:
            return LOSS
        return BREAKEVEN

    @property
    def outcomes(self) -> str:
        return ", ".join(f"TP{leg.tp_row}: {leg.outcome}" for leg in self.legs)


def is_friday_close(when: datetime, friday_close: time) -> bool:
    if when.weekday() in (5, 6):
        return True
    return when.weekday() == 4 and when.time() >= friday_close


def classify_close(deal: ClosedDeal, tolerance: float, friday_close: time) -> str:
    if deal.reason == "TP":
        return "TP"
    if deal.reason == "SL":
        if deal.sl_at_close > 0 and abs(deal.sl_at_close - deal.open_price) <= tolerance + 1e-9:
            return BREAKEVEN
        return "SL"
    if deal.reason == "EXPERT":
        return "Friday close" if is_friday_close(deal.closed, friday_close) else "Closed by EA"
    if deal.reason in ("CLIENT", "MOBILE", "WEB"):
        return "Manual"
    if deal.reason == "SO":
        return "Stop out"
    return deal.reason or "Closed"


def _month_of(when: datetime) -> tuple[int, int]:
    return when.year, when.month


def build_month(
    journal: Journal,
    year: int,
    month: int,
    tolerance: float,
    friday_close: time,
) -> dict[int, list[Trade]]:
    """Trades whose first order was placed in the month (Israel time), grouped by slot.

    The EA numbers trades per group by the month they were placed in, so this keeps the
    N sequence of one month together even when a trade closes in the next month.
    """
    trades: dict[tuple[int, int], Trade] = {}

    def trade_for(tag, side: str) -> Trade:
        key = (tag.group, tag.number)
        if key not in trades:
            trades[key] = Trade(group=tag.group, number=tag.number, strategy=tag.strategy, side=side)
        return trades[key]

    by_position: dict[int, list[ClosedDeal]] = defaultdict(list)
    for deal in journal.closed:
        if _month_of(deal.placed) == (year, month):
            by_position[deal.position].append(deal)
    open_positions = {
        item.ticket for item in journal.open if item.kind == "position" and _month_of(item.placed) == (year, month)
    }
    for position, deals in by_position.items():
        deals.sort(key=lambda d: d.closed)
        first, last = deals[0], deals[-1]
        still_open = position in open_positions
        trade_for(first.tag, first.side).legs.append(
            Leg(
                tp_row=first.tag.tp_row,
                side=first.side,
                lot=round(sum(d.lot for d in deals), 2),
                placed=first.placed,
                opened=first.opened,
                closed=None if still_open else last.closed,
                entry=first.open_price,
                exit=last.close_price,
                sl=first.initial_sl,
                tp=first.initial_tp,
                profit=round(sum(d.net_profit for d in deals), 2),
                outcome=OPEN if still_open else classify_close(last, tolerance, friday_close),
            )
        )
    for item in journal.open:
        if _month_of(item.placed) != (year, month):
            continue
        if item.kind == "position" and item.ticket in by_position:
            continue  # partly closed: already listed, marked open
        trade_for(item.tag, item.side).legs.append(
            Leg(
                tp_row=item.tag.tp_row,
                side=item.side,
                lot=item.lot,
                placed=item.placed,
                opened=item.opened,
                closed=None,
                entry=item.open_price,
                exit=None,
                sl=item.sl,
                tp=item.tp,
                profit=round(item.profit, 2) if item.kind == "position" else 0.0,
                outcome=OPEN,
            )
        )
    for order in journal.unfilled:
        if order.placed is None or _month_of(order.placed) != (year, month):
            continue
        trade_for(order.tag, order.side).legs.append(
            Leg(
                tp_row=order.tag.tp_row,
                side=order.side,
                lot=order.lot,
                placed=order.placed,
                opened=None,
                closed=order.deleted,
                entry=order.entry,
                exit=None,
                sl=order.sl,
                tp=order.tp,
                profit=0.0,
                outcome=_NOT_EXECUTED_REASONS.get(order.reason, f"{NOT_EXECUTED} — {order.reason}"),
            )
        )

    out: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades.values():
        trade.legs.sort(key=lambda leg: leg.tp_row)
        out[trade.group].append(trade)
    for group in out:
        out[group].sort(key=lambda t: t.number)
    return dict(out)


@dataclass(frozen=True)
class Summary:
    trades: int
    executed: int
    not_executed: int
    open: int
    wins: int
    losses: int
    breakeven: int
    profit: float

    @property
    def win_rate(self) -> float | None:
        decided = self.wins + self.losses + self.breakeven
        return self.wins / decided if decided else None


def summarize(trades: list[Trade]) -> Summary:
    results = [t.result for t in trades]
    return Summary(
        trades=len(trades),
        executed=sum(1 for r in results if r != NOT_EXECUTED),
        not_executed=results.count(NOT_EXECUTED),
        open=results.count(OPEN),
        wins=results.count(PROFIT),
        losses=results.count(LOSS),
        breakeven=results.count(BREAKEVEN),
        profit=round(sum(t.profit for t in trades), 2),
    )
