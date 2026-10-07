# Sends the collector's READ credentials from this Windows account to the server. Started by Gev. Nothing secret is printed.
# Takes: the read token from the user variable YANDEX_OAUTH_TOKEN and the Beget API password from its file.
# Never takes: YANDEX_ACTIONS_TOKEN, the Avito keys, any mail credential.
# The values travel inside the SSH connection on standard input. They are not on any command line and not in any log.
# On the server reader_provision.py writes them to /etc/kryuk24-api-read (0750) as two files (0640, root:kryuk-api-read).
param([string]$Server = 'kryuk@155.212.223.79', [string]$Key = "$HOME\.ssh\kryuk24_vps_ed25519", [string]$BegetLogin = 'amo777z0')
$ErrorActionPreference = 'Stop'

$token = [Environment]::GetEnvironmentVariable('YANDEX_OAUTH_TOKEN', 'User')
if (-not $token) { Write-Host 'STOP: the user variable YANDEX_OAUTH_TOKEN is not set. Nothing was sent.' -ForegroundColor Red; exit 2 }
$file = Join-Path $HOME '.ssh\kryuk24_beget_api_password.txt'
if (-not (Test-Path $file)) { Write-Host 'STOP: the Beget API password file is missing. Nothing was sent.' -ForegroundColor Red; exit 2 }
$password = (Get-Content -Raw -LiteralPath $file).Trim()
if (-not $password) { Write-Host 'STOP: the Beget API password file is empty. Nothing was sent.' -ForegroundColor Red; exit 2 }

$json = @{ yandex_read_token = $token; beget_login = $BegetLogin; beget_api_password = $password } | ConvertTo-Json -Compress
$token = $null; $password = $null
$answer = $json | & ssh -i $Key -o BatchMode=yes $Server 'sudo /usr/bin/python3 /opt/kryuk24/reader_provision.py --dir /etc/kryuk24-api-read --group kryuk-api-read'
$code = $LASTEXITCODE
$json = $null
Write-Host $answer
if ($code -ne 0) { Write-Host ("STOP: the server did not store the credentials (exit {0})." -f $code) -ForegroundColor Red; exit 1 }
Write-Host 'Stored on the server. Nothing secret was shown here.' -ForegroundColor Green
