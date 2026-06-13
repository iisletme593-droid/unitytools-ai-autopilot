# Chat AI modelini Cloudflare Workers AI (70B Llama) yap
#
# Calistir:
#   powershell -ExecutionPolicy Bypass -File C:\dev\unitytools-ai-autopilot\scripts\use_cloudflare.ps1
#
# Yaptiklari:
#   1. Arac reposunu gunceller (cloudflare destegini ceker)
#   2. Cloudflare Account ID + API Token sorar (model varsayilani 70B Llama)
#   3. C:\dev\unitytools-ai-autopilot\.env dosyasini gunceller:
#        UNITYTOOLS_PROVIDER=cloudflare + CLOUDFLARE_* anahtarlari
#   4. `unitytools doctor` ile baglanti + yetkiyi dogrular
#
# Sonra Unity panelinde chat'i yeniden baslat; artik 70B Cloudflare modeli kullanilir.

$ErrorActionPreference = "Continue"
$InstallDir = "C:\dev\unitytools-ai-autopilot"
$DefaultModel = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

# .env icinde bir anahtari guncelle ya da ekle (ASCII, satir-bazli).
function Set-EnvKey($path, $key, $value) {
    $lines = if (Test-Path $path) { @(Get-Content $path) } else { @() }
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=") { $found = $true; "$key=$value" }
        else { $line }
    }
    if (-not $found) { $out += "$key=$value" }
    Set-Content -Path $path -Value $out -Encoding ascii
}

# ---------------------------------------------------------------- 0. repo guncel
Write-Step "Arac reposu guncelleniyor"
if (-not (Test-Path (Join-Path $InstallDir ".git"))) { throw "Repo yok: $InstallDir (once setup_windows.ps1)." }
git -C $InstallDir fetch origin | Out-Null
git -C $InstallDir pull --ff-only origin (git -C $InstallDir rev-parse --abbrev-ref HEAD) | Out-Null
Write-Ok "Repo: $(git -C $InstallDir log -1 --format='%h %s')"

$unitytoolsExe = Join-Path $InstallDir ".venv\Scripts\unitytools.exe"
if (-not (Test-Path $unitytoolsExe)) { throw "unitytools kurulu degil (once setup_windows.ps1)." }

# ---------------------------------------------------------------- 1. bilgiler
Write-Step "Cloudflare bilgileri"
Write-Host "  Account ID:  dash.cloudflare.com > sag ustteki hesap > Account ID kopyala"
Write-Host "  API Token:   dash.cloudflare.com/profile/api-tokens > Create Token > 'Workers AI'"
Write-Host ""
$accountId = (Read-Host "Cloudflare Account ID").Trim()
$apiToken  = (Read-Host "Cloudflare API Token").Trim()
$model     = (Read-Host "Model (Enter = $DefaultModel)").Trim()
if (-not $model) { $model = $DefaultModel }

if (-not $accountId -or -not $apiToken) {
    throw "Account ID ve API Token zorunlu. Bos birakildi, islem iptal."
}

# ---------------------------------------------------------------- 2. .env yaz
Write-Step ".env guncelleniyor"
$envFile = Join-Path $InstallDir ".env"
Set-EnvKey $envFile "UNITYTOOLS_PROVIDER" "cloudflare"
Set-EnvKey $envFile "CLOUDFLARE_ACCOUNT_ID" $accountId
Set-EnvKey $envFile "CLOUDFLARE_API_TOKEN" $apiToken
Set-EnvKey $envFile "CLOUDFLARE_MODEL" $model
Write-Ok "Provider=cloudflare, model=$model olarak ayarlandi: $envFile"

# ---------------------------------------------------------------- 3. dogrula
Write-Step "Baglanti dogrulaniyor (unitytools doctor)"
Push-Location $InstallDir
& $unitytoolsExe doctor
Pop-Location

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  CHAT MODELI ARTIK: $model" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Yukarida 'Cloudflare: [OK] reachable + authorized' gorduysen hazirsin." -ForegroundColor Cyan
Write-Host "Unity panelindeki chat-server'i yeniden baslat (kapat/ac) - 70B model devreye girer."
Write-Host ""
Write-Host "Geri donmek istersen .env icinde UNITYTOOLS_PROVIDER=anthropic (veya ollama) yap."
