param(
    [string]$EnvFile    = "D:\Adnan\NewPC\D\UnityToolsV2\.env",
    [string]$Model      = "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    [string]$InstallEnv = "C:\dev\unitytools-ai-autopilot\.env",
    [string]$AccountId  = ""   # .env'de account id yoksa elle ver
)

# Cloudflare anahtarlarini 70B modeline karsi tek tek dener, calismani bulur.
# GUVENLIK: yalnizca CLOUDFLARE/CF adli anahtarlari okur; baska sirlara (cron,
# borsa, AWS vb.) dokunmaz, yazdirmaz. Anahtarlar yalnizca Cloudflare API'sine gider.
#
# Calistir:
#   powershell -ExecutionPolicy Bypass -File C:\dev\unitytools-ai-autopilot\scripts\test_cloudflare_keys.ps1

$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Step($m){ Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "    [OK] $m" -ForegroundColor Green }
function Write-Bad($m){ Write-Host "    [X] $m" -ForegroundColor Red }
function Write-Warn2($m){ Write-Host "    [!] $m" -ForegroundColor Yellow }
function Mask($s){ if(-not $s -or $s.Length -le 10){return '****'}; return $s.Substring(0,6) + '...' + $s.Substring($s.Length-4) }

function Read-EnvMap($path){
    $map = [ordered]@{}
    if (-not (Test-Path $path)) { Write-Warn2 "Bulunamadi: $path"; return $map }
    foreach ($line in Get-Content -LiteralPath $path) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $i = $t.IndexOf("=")
        if ($i -lt 1) { continue }
        $k = $t.Substring(0, $i).Trim()
        $v = $t.Substring($i + 1).Trim().Trim('"').Trim("'")
        if ($v) { $map[$k] = $v }
    }
    return $map
}

function Set-EnvKey($path, $key, $value){
    $lines = if (Test-Path $path) { @(Get-Content -LiteralPath $path) } else { @() }
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=") { $found = $true; "$key=$value" }
        else { $line }
    }
    if (-not $found) { $out += "$key=$value" }
    Set-Content -LiteralPath $path -Value $out -Encoding ascii
}

# ---------------------------------------------------------------- 1. anahtarlari topla
Write-Step "Anahtarlar okunuyor: $EnvFile"
$map = Read-EnvMap $EnvFile

$accounts = New-Object System.Collections.Generic.List[string]
$tokens   = New-Object System.Collections.Generic.List[string]
if ($AccountId) { $accounts.Add($AccountId) }

foreach ($k in $map.Keys) {
    $v = $map[$k]; $ku = $k.ToUpperInvariant()
    if ($v -match '^[0-9a-fA-F]{32}$') { $accounts.Add($v); continue }   # account id = 32 hex
    if ($ku -like '*ACCOUNT*') { $accounts.Add($v); continue }
    # Token: yalnizca cloudflare/cf adli anahtarlardan (cron/borsa anahtarlari haric)
    if ($ku -like '*CLOUDFLARE*' -or $ku -like 'CF_*' -or $ku -like '*WORKERS*AI*') {
        if ($ku -like '*TOKEN*' -or $ku -like '*KEY*' -or $ku -like '*API*' -or $v.Length -ge 20) {
            $tokens.Add($v)
        }
    }
}
$accounts = @($accounts | Select-Object -Unique)
$tokens   = @($tokens   | Select-Object -Unique)

Write-Host "    Bulunan account id: $($accounts.Count), token: $($tokens.Count)"
foreach ($k in $map.Keys) {
    $ku = $k.ToUpperInvariant()
    if ($ku -like '*CLOUDFLARE*' -or $ku -like 'CF_*' -or $ku -like '*WORKERS*AI*' -or $ku -like '*ACCOUNT*') {
        Write-Host "      $k = $(Mask $map[$k])"
    }
}

if ($accounts.Count -eq 0) {
    $manual = (Read-Host "Account ID bulunamadi. Cloudflare Account ID gir").Trim()
    if ($manual) { $accounts = @($manual) } else { throw "Account ID olmadan test yapilamaz." }
}
if ($tokens.Count -eq 0) { throw "Hic Cloudflare token'i bulunamadi (anahtar adi CLOUDFLARE/CF icermeli)." }

# ---------------------------------------------------------------- 2. dene
function Test-Combo($acct, $token, $model){
    $url = "https://api.cloudflare.com/client/v4/accounts/$acct/ai/v1/chat/completions"
    $body = @{ model = $model; messages = @(@{ role = "user"; content = "ping" }); max_tokens = 1 } |
        ConvertTo-Json -Depth 6 -Compress
    try {
        $resp = Invoke-WebRequest -Uri $url -Method Post -ContentType "application/json" `
            -Headers @{ Authorization = "Bearer $token" } -Body $body -UseBasicParsing -TimeoutSec 25
        return @{ ok = $true; code = [int]$resp.StatusCode }
    } catch {
        $code = -1; $detail = $_.Exception.Message
        if ($_.Exception.Response) {
            try { $code = [int]$_.Exception.Response.StatusCode } catch {}
            try {
                $sr = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
                $detail = $sr.ReadToEnd(); $sr.Close()
            } catch {}
        }
        return @{ ok = $false; code = $code; detail = $detail }
    }
}

Write-Step "70B modeline erisim deneniyor ($Model)"
$winner = $null
foreach ($token in $tokens) {
    foreach ($acct in $accounts) {
        Write-Host "  -> account $(Mask $acct) + token $(Mask $token) ... " -NoNewline
        $r = Test-Combo $acct $token $Model
        if ($r.ok) {
            Write-Host "BASARILI (HTTP $($r.code))" -ForegroundColor Green
            $winner = @{ acct = $acct; token = $token }
            break
        } else {
            $hint = switch ($r.code) {
                401 { "yetkisiz (token gecersiz)" }
                403 { "token'da Workers AI izni yok" }
                404 { "account id yanlis veya model bu hesapta yok" }
                default { "HTTP $($r.code)" }
            }
            Write-Host "olmadi - $hint" -ForegroundColor Red
        }
    }
    if ($winner) { break }
}

if (-not $winner) {
    Write-Host ""
    Write-Bad "Hicbir kombinasyon 70B modeline ulasamadi."
    Write-Host "  En olasi sebep: token'da 'Workers AI' izni yok ya da account id eslesmedi." -ForegroundColor Yellow
    Write-Host "  Cozum: dash.cloudflare.com/profile/api-tokens > Create Token > 'Workers AI' template." -ForegroundColor Yellow
    exit 1
}

# ---------------------------------------------------------------- 3. calisan anahtari kur
Write-Step "Calisan anahtar install .env'e yaziliyor: $InstallEnv"
if (-not (Test-Path (Split-Path $InstallEnv))) { throw "Install klasoru yok: $(Split-Path $InstallEnv). Once setup_windows.ps1." }
Set-EnvKey $InstallEnv "UNITYTOOLS_PROVIDER" "cloudflare"
Set-EnvKey $InstallEnv "CLOUDFLARE_ACCOUNT_ID" $winner.acct
Set-EnvKey $InstallEnv "CLOUDFLARE_API_TOKEN" $winner.token
Set-EnvKey $InstallEnv "CLOUDFLARE_MODEL" $Model
Write-Ok "Yazildi. Provider=cloudflare, model=$Model"

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  CALISAN ANAHTAR BULUNDU VE KURULDU" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  account: $(Mask $winner.acct)   token: $(Mask $winner.token)"
Write-Host ""
Write-Host "Son adim: Unity panelindeki chat-server'i kapat/ac - 70B Cloudflare devreye girer." -ForegroundColor Cyan
Write-Host ""
Write-Warn2 "Guvenlik: $EnvFile icinde borsa/cron/AWS gibi sirlar da varsa, bunlari"
Write-Warn2 "proje .env'inden ayri, sifreli bir yerde tut. Bu script onlara dokunmadi."
