# Started by Gev in his own terminal. Sets the password of Armen's portal account on the server.
# The password is typed into the server's hidden prompt, twice. It is not on a command line, not in a file
# on this computer and not in any log; Claude does not see it.
# Before sending the terminal's output to anybody, look at it: it must hold no password.
param([string]$Server = 'kryuk@155.212.223.79', [string]$Key = "$HOME\.ssh\kryuk24_vps_ed25519",
      [ValidateSet('armen', 'gev')][string]$Account = 'armen')
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'provision.sh'
& scp -q -i $Key -o BatchMode=yes $script "${Server}:/tmp/armen_provision.sh"
if ($LASTEXITCODE -ne 0) { Write-Host 'STOP: the script was not copied. Nothing changed.' -ForegroundColor Red; exit 1 }
& ssh -t -i $Key $Server "sudo sh /tmp/armen_provision.sh $Account; rm -f /tmp/armen_provision.sh"
if ($LASTEXITCODE -ne 0) { Write-Host 'STOP: the server reported a failure.' -ForegroundColor Red; exit 1 }
Write-Host 'Done. Nothing secret was shown here.' -ForegroundColor Green
