# Read-only check of the stored Yandex token: Metrica counters and goals, Webmaster hosts and indexing summary.
# Prints data only. Never prints the token.
#   -Kind read (default)  token YANDEX_OAUTH_TOKEN
#   -Kind actions         token YANDEX_ACTIONS_TOKEN; also one read-only call to the Direct API (list of campaigns)
param([ValidateSet('read', 'actions')][string]$Kind = 'read')
$ErrorActionPreference = 'Stop'
$variable = if ($Kind -eq 'actions') { 'YANDEX_ACTIONS_TOKEN' } else { 'YANDEX_OAUTH_TOKEN' }
$token = [Environment]::GetEnvironmentVariable($variable, 'User')
if (-not $token) { Write-Host "NO TOKEN: the user variable $variable is not set." -ForegroundColor Red; exit 2 }
$headers = @{ Authorization = "OAuth $token" }
$failed = 0

function Call($label, $uri) {
    try { return Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 30 }
    catch {
        $code = $null; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        Write-Host ("FAIL {0}: HTTP {1}" -f $label, $code) -ForegroundColor Red
        $script:failed++
        return $null
    }
}

Write-Host '--- Metrica'
$counters = Call 'metrica counters' 'https://api-metrika.yandex.net/management/v1/counters'
if ($counters) {
    Write-Host ("counters visible: {0}" -f $counters.rows)
    foreach ($c in $counters.counters) {
        Write-Host ("  id {0}  {1}  site {2}  status {3}" -f $c.id, $c.name, $c.site, $c.code_status)
        $goals = Call "metrica goals $($c.id)" ("https://api-metrika.yandex.net/management/v1/counter/{0}/goals" -f $c.id)
        if ($goals) { Write-Host ("    goals: {0}" -f (($goals.goals | ForEach-Object { "$($_.id)=$($_.name)" }) -join '; ')) }
        $stat = Call "metrica stat $($c.id)" ("https://api-metrika.yandex.net/stat/v1/data?ids={0}&metrics=ym:s:visits,ym:s:users&date1=7daysAgo&date2=yesterday" -f $c.id)
        if ($stat) { Write-Host ("    last 7 days: visits {0}, users {1}" -f $stat.totals[0], $stat.totals[1]) }
    }
}

Write-Host '--- Webmaster'
$user = Call 'webmaster user' 'https://api.webmaster.yandex.net/v4/user'
if ($user) {
    $hosts = Call 'webmaster hosts' ("https://api.webmaster.yandex.net/v4/user/{0}/hosts" -f $user.user_id)
    if ($hosts) {
        Write-Host ("hosts: {0}" -f @($hosts.hosts).Count)
        foreach ($h in $hosts.hosts) {
            Write-Host ("  {0}  verified: {1}" -f $h.unicode_host_url, $h.verified)
            if ($h.verified) {
                $sum = Call "webmaster summary" ("https://api.webmaster.yandex.net/v4/user/{0}/hosts/{1}/summary" -f $user.user_id, [uri]::EscapeDataString($h.host_id))
                if ($sum) { Write-Host ("    pages in search: {0}, excluded: {1}, site quality index: {2}" -f $sum.searchable_pages_count, $sum.excluded_pages_count, $sum.sqi) }
            }
        }
    }
}
if ($Kind -eq 'actions') {
    Write-Host '--- Direct (read-only: campaigns.get)'
    $body = '{"method":"get","params":{"SelectionCriteria":{},"FieldNames":["Id","Name","State","Status","Funds"]}}'
    try {
        $d = Invoke-RestMethod -Method Post -Uri 'https://api.direct.yandex.com/json/v5/campaigns' -TimeoutSec 30 -ContentType 'application/json; charset=utf-8' `
            -Headers @{ Authorization = "Bearer $token"; 'Accept-Language' = 'ru' } -Body $body
        if ($d.error) {
            Write-Host ("Direct API error {0}: {1} / {2}" -f $d.error.error_code, $d.error.error_string, $d.error.error_detail) -ForegroundColor Yellow
            $failed++
        } else {
            Write-Host ("campaigns: {0}" -f @($d.result.Campaigns).Count)
            foreach ($c in $d.result.Campaigns) { Write-Host ("  {0}  {1}  state {2}  status {3}" -f $c.Id, $c.Name, $c.State, $c.Status) }
        }
    } catch {
        $code = $null; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        Write-Host ("FAIL direct campaigns: HTTP {0}" -f $code) -ForegroundColor Red
        $failed++
    }
}
$token = $null
if ($failed) { Write-Host "DONE with $failed failed call(s)." -ForegroundColor Red; exit 1 }
Write-Host 'DONE: every call answered.' -ForegroundColor Green
