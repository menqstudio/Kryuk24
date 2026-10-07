# Launcher for ONE supervised trial case. Started by Gev by hand from a plain PowerShell window.
# This is the ONLY way a case is started. No other script starts it, waits for it or repeats it.
# It closes nothing and kills nothing. If another work window is open it says which one and stops.
# A second start while one is running is refused by the harness itself (exclusive lock held by Windows).
# It cannot tell how many browsers are connected: before the start, the main profile's Claude extension is
# disconnected by hand; the real browser list is confirmed by check T1.8 of the run.
#   -Case T1 -RerunReason "..."            dry: every check, no model run
#   -Case T1 -RerunReason "..." -Execute   the same, then exactly one run of that case. No retry.
param(
    [Parameter(Mandatory = $true)][string]$Case,
    [string]$RerunReason = '',
    [switch]$Execute
)
$ErrorActionPreference = 'Continue'
$run = 'C:\Users\Admin\KRYUK24-Bro-Trial'
$pkg = Split-Path -Parent $MyInvocation.MyCommand.Path
# One log per start: the name carries dry/execute, the time to the millisecond and this process id, so two starts never share a file.
$mode = if ($Execute) { 'execute' } else { 'dry' }
$log = Join-Path $run ('{0}_{1}_console_{2}_pid{3}.txt' -f $Case, $mode, (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ'), $PID)
function Say($t) { $t | Tee-Object -FilePath $log -Append }
function ChromeIds { @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CreationDate.ToUniversalTime().ToString('o') } | Sort-Object) }

Say "Launcher for $Case. Execute: $($Execute.IsPresent). Nothing is closed or killed by this script."

Say '1/4 fake page server'
$alive = $false
try { $alive = (Invoke-WebRequest 'http://127.0.0.1:18765/health' -UseBasicParsing -TimeoutSec 5).Content -eq 'ok' } catch {}
if (-not $alive) {
    Say 'STOP: the fake page server does not answer on 127.0.0.1:18765. Start fixture_server.py first (see TRIAL_PLAN.md, section 7). Nothing was run.'
    exit 3
}

Say '2/4 preflight (P8: extensions of Trial A, P9: other work windows, P10: one recognised native host; none of them counts connected browsers)'
python "$pkg\run_trial.py" --run-dir $run --preflight 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) {
    Say 'STOP: preflight is not all PASS. Close the named windows by hand (VS Code, Claude Code, Claude desktop, other Chrome profiles) and start again. Nothing was run.'
    exit 4
}

Say '3/4 Chrome must be at rest: two process lists 30 s apart have to be identical'
$first = ChromeIds
Start-Sleep -Seconds 30
$second = ChromeIds
if ($first.Count -eq 0 -or (Compare-Object $first $second)) {
    Say ('STOP: the set of chrome.exe processes changed within 30 s ({0} -> {1}). Leave the Trial A window alone for a minute and start again. Nothing was run.' -f $first.Count, $second.Count)
    exit 5
}
Say ("    {0} chrome.exe processes, unchanged" -f $first.Count)

if (-not $Execute) {
    Say '4/4 DRY: every check passed. No model run was started (no -Execute).'
    exit 0
}

Say "4/4 ${Case}: one run, no retry. Watch the Trial A window."
$cmd = @("$pkg\run_trial.py", '--run-dir', $run, '--execute', '--case', $Case, '--confirm', 'I am watching the trial profile')
if ($RerunReason) { $cmd += @('--rerun-reason', $RerunReason) }
python @cmd 2>&1 | Tee-Object -FilePath $log -Append
Say ("$Case exit code: $LASTEXITCODE")
Say 'DONE. Run nothing else.'
