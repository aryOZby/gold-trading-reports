# Registers a daily Windows task that runs the monthly report with no console window.
# The report for the previous month is sent once, on the first run of each month.
# Run in PowerShell as Administrator:
#   powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1

param(
    [string]$TaskName = "GoldTradingReports",
    [string]$At = "09:00"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Pythonw)) { throw "Missing $Pythonw - create the venv first" }

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "main.py" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
# StartWhenAvailable: if the server was off at the scheduled time, run as soon as it is back.
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
# S4U: runs whether or not anyone is logged in, without storing a password.
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null

Write-Host ""
Write-Host "Scheduled task '$TaskName' runs daily at $At (server time)." -ForegroundColor Green
Write-Host "  folder : $Root"
Write-Host "  log    : $Root\logs\reports.log"
Write-Host ""
Write-Host "  Start-ScheduledTask -TaskName $TaskName       # run now"
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
