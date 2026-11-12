# Gold Trading — Monthly Reports

Reporting service for the gold-trading desk. Once a month it turns the Chart Executor's trade journal into one Excel file per Telegram group and emails them. It never talks to Telegram or MetaTrader and never trades.

| Service | Role |
|---|---|
| [Telegram Group Listener](https://github.com/aryOZby/gold-signal-listener) | Listen to groups by chat id and hand off each recognized signal |
| [Chart Executor](https://github.com/aryOZby/gold-trading-chart-executor) | Read those signals on the MT5 chart and trade them |
| **Monthly Reports** (this repo) | Build monthly Excel tables per group and email them |

## Source data

The Chart Executor EA keeps a journal in MT5 `Common\Files\gt_journal\` (Israel time):

- `closed.csv` — every closing deal, rebuilt from the broker history
- `open.csv` — snapshot of running positions and pending orders
- `unfilled.csv` — pending orders deleted without filling, with the reason

Each position carries the comment `S<strategy>|G<group>|N<number>|tp<row>`. A **trade** is one signal: all positions with the same group and N. N restarts at 1 for every group each month, and a trade belongs to the month its orders were placed in.

## The report

One workbook per group per month, `reports\2026-11\2026-11 G2 Technical Pips.xlsx`:

| Sheet | Content |
|---|---|
| Trades | One row per N: strategy, side, placed / opened / closed date and time, positions, lot, entry, SL, TPs hit, result, net profit, and the outcome of every position |
| Positions | One row per position or order: TP row, times, entry, exit, SL, TP, outcome, net profit |
| Summary | Totals for the month and a per-strategy breakdown with win rate |

Results: **Profit**, **Loss**, **Breakeven** (net zero), **Open** (still running when the report was built), **Not executed** (every order deleted before filling — expired, TP1 reached first, breakeven, or Friday close).

Position outcomes: `TP`, `SL`, `Breakeven` (stopped at the entry after the SL was moved), `Friday close`, `Closed by EA`, `Manual`, `Stop out`, or the not-executed reason. Net profit includes commission and swap.

The email has a one-table summary of all groups and the workbooks attached.

## Setup (Windows VPS)

```bat
cd C:\Users\Administrator
git clone https://github.com/aryOZby/gold-trading-reports.git
cd gold-trading-reports
copy config.example.yaml config.yaml
copy .env.example .env
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In `config.yaml` set `email.username` (the sending Gmail address) and `email.to`. In `.env` set `SMTP_PASSWORD` to a Gmail [App Password](https://myaccount.google.com/apppasswords) — not the account password.

Test without email, then with email for the current month:

```bat
.venv\Scripts\python.exe main.py --month 2026-11 --no-email
.venv\Scripts\python.exe main.py --month 2026-11
```

Schedule it (PowerShell as Administrator). It runs daily with no window and sends the previous month once, on the first run of each month:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1
```

Log: `logs\reports.log`. Sent months are recorded in `data\sent.json`; `--month YYYY-MM` rebuilds and resends any month.
