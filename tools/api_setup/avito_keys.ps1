# Stores the Avito API keys without anyone typing them. Started by Gev. Nothing secret is printed.
# On the Avito page "Integrations and API" (after the "get keys" button) there are two values: Client ID and Client Secret.
# The script asks to copy each one with the copy button on the page, takes it from the clipboard, stores it in the
# user environment variables AVITO_CLIENT_ID / AVITO_CLIENT_SECRET, then makes two read-only calls:
# gets a token and asks Avito whose account it is. The account number goes to AVITO_PROFILE_ID.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

function Clip($clear) {
    for ($i = 0; $i -lt 15; $i++) {
        try {
            if ($clear) { [System.Windows.Forms.Clipboard]::Clear(); return '' }
            return [System.Windows.Forms.Clipboard]::GetText()
        } catch { Start-Sleep -Milliseconds 300 }
    }
    return $null
}

function Take($label) {
    [void](Clip $true)
    Write-Host ''
    Write-Host ("On the Avito page press the COPY button next to {0}, then come back and press Enter." -f $label) -ForegroundColor Yellow
    [void](Read-Host 'Enter when copied')
    $value = Clip $false
    [void](Clip $true)
    if ($null -eq $value) { return $null }
    $value = $value.Trim()
    if ($value -notmatch '^[A-Za-z0-9_\-]{10,120}$') { return $null }
    return $value
}

$id = Take 'Client ID'
if (-not $id) { Write-Host 'STOP: the clipboard did not hold a Client ID. Nothing was saved.' -ForegroundColor Red; exit 2 }
$secret = Take 'Client Secret'
if (-not $secret) { Write-Host 'STOP: the clipboard did not hold a Client Secret. Nothing was saved.' -ForegroundColor Red; $id = $null; exit 2 }
if ($id -eq $secret) { Write-Host 'STOP: the same value was copied twice. Nothing was saved.' -ForegroundColor Red; exit 2 }

try {
    $token = Invoke-RestMethod -Method Post -Uri 'https://api.avito.ru/token' -TimeoutSec 30 -Body @{ grant_type = 'client_credentials'; client_id = $id; client_secret = $secret }
} catch {
    $code = $null; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
    Write-Host ("STOP: Avito did not give a token (HTTP {0}). The keys were NOT saved. Copy them again and restart." -f $code) -ForegroundColor Red
    $id = $null; $secret = $null
    exit 1
}
if (-not $token.access_token) { Write-Host 'STOP: Avito answered without a token. The keys were NOT saved.' -ForegroundColor Red; exit 1 }

[Environment]::SetEnvironmentVariable('AVITO_CLIENT_ID', $id, 'User')
[Environment]::SetEnvironmentVariable('AVITO_CLIENT_SECRET', $secret, 'User')
$id = $null; $secret = $null
Write-Host 'Keys accepted by Avito and saved to the user variables AVITO_CLIENT_ID and AVITO_CLIENT_SECRET. Clipboard emptied.' -ForegroundColor Green

try {
    $me = Invoke-RestMethod -Uri 'https://api.avito.ru/core/v1/accounts/self' -TimeoutSec 30 -Headers @{ Authorization = "Bearer $($token.access_token)" }
    [Environment]::SetEnvironmentVariable('AVITO_PROFILE_ID', [string]$me.id, 'User')
    Write-Host ("Account: id {0}, name {1}. Saved AVITO_PROFILE_ID." -f $me.id, $me.name) -ForegroundColor Green
} catch {
    $code = $null; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
    Write-Host ("The token works, but the account call failed (HTTP {0}). AVITO_PROFILE_ID was not saved." -f $code) -ForegroundColor Yellow
}
$token = $null
