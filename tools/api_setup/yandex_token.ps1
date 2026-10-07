# Stores a Yandex OAuth token without anyone typing it. Started by Gev. The token is never printed.
#   -Kind read      app "KRYUK24 Bro"         (Metrica read, Webmaster)                 -> YANDEX_OAUTH_TOKEN
#   -Kind actions   app "KRYUK24 Bro Actions" (Direct API, Metrica read+write, Webmaster) -> YANDEX_ACTIONS_TOKEN
# Steps: opens the Yandex consent page in the KRYUK24 Chrome profile; Gev presses "Allow"; Yandex shows the token on
# its own page; Gev presses the copy button there and comes back. The script takes the token from the clipboard ONLY if
# it looks like a Yandex token, stores it in the user environment variable and empties the clipboard.
param([ValidateSet('read', 'actions')][string]$Kind = 'read')
$ErrorActionPreference = 'Stop'
$apps = @{
    read    = @{ id = '6a02b3eadf244e53a5a4169fcfa8a956'; var = 'YANDEX_OAUTH_TOKEN';   name = 'KRYUK24 Bro';         rights = 'Metrica (read) and Webmaster' }
    actions = @{ id = '7aa02a1bb2c94531af2af76ac345bb45'; var = 'YANDEX_ACTIONS_TOKEN'; name = 'KRYUK24 Bro Actions'; rights = 'Direct, Metrica (read and write) and Webmaster' }
}
$app = $apps[$Kind]                                   # the ids are public application ids, not secrets
$url = "https://oauth.yandex.ru/authorize?response_type=token&client_id=$($app.id)"
Add-Type -AssemblyName System.Windows.Forms

function Clip($text) {
    for ($i = 0; $i -lt 15; $i++) {
        try {
            if ($null -eq $text) { [System.Windows.Forms.Clipboard]::Clear(); return '' }
            return [System.Windows.Forms.Clipboard]::GetText()
        } catch { Start-Sleep -Milliseconds 300 }
    }
    return $null
}

[void](Clip $null)
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' '--profile-directory=Profile KRYUK24' $url
Write-Host ''
Write-Host 'In the Chrome window that opened (account smbatyan.armen82):' -ForegroundColor Yellow
Write-Host ("  1) check that the app is ""{0}"" and the rights are {1}" -f $app.name, $app.rights)
Write-Host '  2) press Allow'
Write-Host '  3) on the next page press the COPY button next to the token'
Write-Host 'Then come back here and press Enter. Do not paste the token anywhere.' -ForegroundColor Yellow
[void](Read-Host 'Enter when the token is copied')

$clip = Clip 'read'
[void](Clip $null)
if ($null -eq $clip -or $clip -notmatch '^y[0-9]_[A-Za-z0-9_\-]{30,200}$') {
    Write-Host 'STOP: what was in the clipboard does not look like a Yandex token. Nothing was saved, the clipboard was emptied.' -ForegroundColor Red
    Write-Host 'Start this script again and use the copy button on the Yandex page.'
    $clip = $null
    exit 2
}
[Environment]::SetEnvironmentVariable($app.var, $clip, 'User')
$length = $clip.Length
$clip = $null
Write-Host ("Saved to the user variable {0} (length {1}). Clipboard emptied." -f $app.var, $length) -ForegroundColor Green
Write-Host 'Checking it now (read-only calls)...'
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'yandex_check.ps1') -Kind $Kind
