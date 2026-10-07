# Sets up the separate Beget API password without anyone typing or seeing it.
# Started by Gev. The script invents a random password once, keeps it in a file only this Windows user can read,
# and puts it on the clipboard so that it can be pasted into Beget's password field. Then it empties the clipboard
# and makes one read-only call (account balance and days left).
# Safe to start again: it never invents a second password while the file exists. If Beget does not accept the stored
# one yet, it puts the SAME password on the clipboard again.
$ErrorActionPreference = 'Stop'
$file = Join-Path $env:USERPROFILE '.ssh\kryuk24_beget_api_password.txt'
$login = 'amo777z0'
Add-Type -AssemblyName System.Windows.Forms

function Clip($text) {
    # The clipboard is shared with every program; it can be busy for a moment. Try a few times, never crash on it.
    for ($i = 0; $i -lt 15; $i++) {
        try {
            if ($null -eq $text) { [System.Windows.Forms.Clipboard]::Clear() } else { [System.Windows.Forms.Clipboard]::SetText($text) }
            return $true
        } catch { Start-Sleep -Milliseconds 300 }
    }
    return $false
}

function Check {
    $secret = [System.IO.File]::ReadAllText($file).Trim()
    try {
        $r = Invoke-RestMethod -Method Post -Uri 'https://api.beget.com/api/user/getAccountInfo' -Body @{ login = $login; passwd = $secret; output_format = 'json' } -TimeoutSec 30
    } catch {
        Write-Host 'The Beget API did not answer (network?).' -ForegroundColor Red
        return $false
    } finally { $secret = $null }
    if ($r.status -ne 'success' -or $r.answer.status -ne 'success') {
        Write-Host ("Beget does not accept the stored password yet: {0} {1}" -f $r.error_text, (($r.answer.errors | ForEach-Object { $_.error_text }) -join '; ')) -ForegroundColor Yellow
        return $false
    }
    $a = $r.answer.result
    Write-Host ("OK. Balance: {0} RUB. Days to block: {1}. Plan: {2}. Daily rate: {3} RUB." -f $a.user_balance, $a.user_days_to_block, $a.plan_name, $a.user_rate_current) -ForegroundColor Green
    return $true
}

if (-not (Test-Path $file)) {
    $alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'.ToCharArray()
    $bytes = New-Object byte[] 28
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    [System.IO.File]::WriteAllText($file, (-join ($bytes | ForEach-Object { $alphabet[$_ % $alphabet.Length] })))
    & icacls $file /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
    Write-Host 'A new API password was created and stored.'
} elseif (Check) {
    exit 0
}

if (-not (Clip ([System.IO.File]::ReadAllText($file).Trim()))) {
    Write-Host 'STOP: the clipboard is busy. Close clipboard tools and start again. Nothing changed.' -ForegroundColor Red
    exit 3
}
Write-Host ''
Write-Host 'The API password is on the clipboard (28 letters and digits).' -ForegroundColor Yellow
Write-Host 'In the Beget tab (Settings - Security - Beget API):'
Write-Host '  1) press "Set a new password for the API" (if the dialog "Change API password" is not open yet)'
Write-Host '  2) first field "current account password": type the Beget ACCOUNT password yourself (the one for the panel)'
Write-Host '  3) "New API password": click into it, Ctrl+V.  "Repeat new password": click into it, Ctrl+V'
Write-Host '  4) press "Change password" and wait until Beget says it is changed'
Write-Host 'ONLY THEN come back here and press Enter.' -ForegroundColor Yellow
[void](Read-Host 'Enter when Beget has saved the password')
if (Clip $null) { Write-Host 'Clipboard emptied.' } else { Write-Host 'WARNING: could not empty the clipboard. Copy any other text now to overwrite it.' -ForegroundColor Red }
Start-Sleep -Seconds 3
if (Check) { exit 0 }
Write-Host 'Not accepted. If Beget showed an error about the password, tell Claude what it said. Starting this script again repeats the same password.' -ForegroundColor Red
exit 1
