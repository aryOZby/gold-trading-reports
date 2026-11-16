# Gold Trading — Monthly Reports

Reporting service for the gold-trading desk. Once a month it turns the Chart Executor's trade journal into one Excel file per Telegram group, emails them, and uploads them to Google Drive. It never talks to Telegram or MetaTrader and never trades.

| Service | Role |
|---|---|
| [Telegram Group Listener](https://github.com/aryOZby/gold-signal-listener) | Listen to groups by chat id and hand off each recognized signal |
| [Chart Executor](https://github.com/aryOZby/gold-trading-chart-executor) | Read those signals on the MT5 chart and trade them |
| **Monthly Reports** (this repo) | Build monthly Excel tables per group, email them, and keep them in Google Drive |

## Source data

The Chart Executor EA keeps a journal per MT5 account in `Common\Files\gt_journal\<account number>\` (Israel time); set `journal_dir` to the account to report on:

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

The email has a one-table summary of all groups, the workbooks attached, and a link to the month's Drive folder.

In Google Drive the workbooks go to `Gold Trading Reports\2026-11\`. Running a month again replaces the files in place. The app uses the `drive.file` scope, so it can only see the folders and files it created.

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

In `config.yaml` set `email.to` and `drive.enabled: true`.

### Google sign-in (one time)

Email is sent through the Gmail API as the signed-in account and the workbooks are uploaded with the same sign-in, so no App Password is needed. (`email.method: smtp` with `SMTP_PASSWORD` in `.env` is still available.)

1. In [Google Cloud Console](https://console.cloud.google.com/), signed in with the account that sends and keeps the reports, create a project.
2. **APIs & Services → Library** → enable **Google Drive API** and **Gmail API**.
3. **APIs & Services → OAuth consent screen**: user type *External*, fill in the app name and emails, then **Publish app** (status *In production*). In *Testing* status the sign-in expires after 7 days.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**, type **Desktop app**. Download the JSON and save it on the server as `secrets\google_client.json`.
5. Sign in once on the server. A browser opens; choose the account, get past the "Google hasn't verified this app" notice (*Advanced → Go to …*), and tick both permissions (Drive files and sending email):

   ```bat
   .venv\Scripts\python.exe scripts\authorize_google.py
   ```

   The token is saved to `secrets\google_token.json` and refreshed automatically. `secrets\` is gitignored.

### Test

Without email and Drive, then everything, for the current month:

```bat
.venv\Scripts\python.exe main.py --month 2026-11 --no-email --no-drive
.venv\Scripts\python.exe main.py --month 2026-11
```

### Schedule

PowerShell as Administrator. It runs daily with no window and delivers the previous month once, on the first run of each month. If the email or the upload fails, only that part is retried on the next run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1
```

Log: `logs\reports.log`. Delivered months are recorded in `data\sent.json`. `--month YYYY-MM` rebuilds and redelivers any month.
