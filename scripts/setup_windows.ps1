# UnityTools AI Autopilot - Windows otomatik kurulum
#
# Tek satirla calistir (PowerShell, normal kullanici yeterli; Git kurulumu UAC sorabilir):
#   irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/claude/beautiful-franklin-llxce2/scripts/setup_windows.ps1 | iex
#
# Yaptiklari:
#   1. Git ve Python yoksa winget ile kurar (PATH'i ayni oturumda tazeler)
#   2. Repoyu C:\dev\unitytools-ai-autopilot'a klonlar / gunceller
#   3. .venv kurar ve paketi yukler (aktivasyon gerektirmez)
#   4. .env olusturur: ANTHROPIC_API_KEY sorar, UNITYTOOLS_BRIDGE_TOKEN uretir, setx ile kalici yapar
#   5. Unity proje yolu verirsen editor eklentisini kurar
#
# Not: Mesajlar PowerShell 5.1 ANSI uyumu icin bilerek aksansiz Turkce.

# Not "Stop": git/winget gibi native araclar ilerleme bilgisini stderr'e yazar ve
# PS 5.1 bunlari Stop modunda hataya cevirebilir. Kritik adimlar exit code ile kontrol edilir.
$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$InstallDir = "C:\dev\unitytools-ai-autopilot"
$RepoUrl    = "https://github.com/iisletme593-droid/unitytools-ai-autopilot.git"
$Branch     = "claude/beautiful-franklin-llxce2"

function Write-Step($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    [!] $msg" -ForegroundColor Yellow }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Test-ToolWorks($name) {
    # Windows'un Store stub'i (WindowsApps\python.exe) Get-Command'da gorunur ama
    # calismaz; o yuzden gercekten --version calistirarak dogrula.
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { return $false }
    & $name --version *> $null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Tool($name, $wingetId, $extraPaths) {
    if (Test-ToolWorks $name) {
        Write-Ok "$name zaten kurulu: $((Get-Command $name).Source)"
        return
    }
    Write-Warn2 "$name bulunamadi/calismiyor, winget ile kuruluyor ($wingetId)..."
    winget install --id $wingetId -e --source winget --accept-package-agreements --accept-source-agreements
    Refresh-Path
    foreach ($p in $extraPaths) {
        if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path += ";$p" }
    }
    if (-not (Test-ToolWorks $name)) {
        throw "$name kurulumdan sonra da bulunamadi. PowerShell'i kapatip acin ve scripti tekrar calistirin."
    }
    Write-Ok "$name kuruldu."
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  UnityTools AI Autopilot - Windows kurulum" -ForegroundColor Magenta
Write-Host "=====================================================" -ForegroundColor Magenta

# ---------------------------------------------------------------- 1. araclar
Write-Step "Gerekli araclar kontrol ediliyor"
Ensure-Tool "git" "Git.Git" @("$env:ProgramFiles\Git\cmd")
Ensure-Tool "python" "Python.Python.3.11" @(
    "$env:LOCALAPPDATA\Programs\Python\Python311",
    "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
)

# ---------------------------------------------------------------- 2. repo
Write-Step "Repo hazirlaniyor: $InstallDir"
$parent = Split-Path $InstallDir -Parent
if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Ok "Mevcut klon bulundu, guncelleniyor..."
    git -C $InstallDir fetch origin
    if ($LASTEXITCODE -ne 0) { throw "git fetch basarisiz (internet/izin?)." }
} else {
    git clone $RepoUrl $InstallDir
    if ($LASTEXITCODE -ne 0) { throw "git clone basarisiz (internet/izin?)." }
}
git -C $InstallDir checkout $Branch
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "Dal '$Branch' bulunamadi (merge edilmis olabilir); main kullaniliyor."
    git -C $InstallDir checkout main
    if ($LASTEXITCODE -ne 0) { throw "git checkout basarisiz." }
}
$currentBranch = git -C $InstallDir rev-parse --abbrev-ref HEAD
git -C $InstallDir pull --ff-only origin $currentBranch
Write-Ok "Repo hazir: $(git -C $InstallDir log -1 --format='%h %s')"

# ---------------------------------------------------------------- 3. venv
Write-Step "Python sanal ortami kuruluyor"
$venvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    python -m venv (Join-Path $InstallDir ".venv")
    if (-not (Test-Path $venvPy)) { throw "venv olusturulamadi (python kurulumunu kontrol et)." }
    Write-Ok "Yeni .venv olusturuldu."
} else {
    Write-Ok "Mevcut .venv kullaniliyor."
}
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -e $InstallDir
if ($LASTEXITCODE -ne 0) { throw "pip install basarisiz. Cikti yukarida." }
Write-Ok "Paket kuruldu (unitytools CLI hazir)."

# ---------------------------------------------------------------- 4. .env
Write-Step ".env yapilandiriliyor"
$envFile = Join-Path $InstallDir ".env"
if (Test-Path $envFile) {
    Write-Ok ".env zaten var, dokunulmadi."
    $tokenLine = (Get-Content $envFile | Where-Object { $_ -match "^UNITYTOOLS_BRIDGE_TOKEN=" } | Select-Object -First 1)
    $token = if ($tokenLine) { $tokenLine.Split("=", 2)[1].Trim() } else { "" }
} else {
    $apiKey = Read-Host "Anthropic API anahtarini yapistir (sk-ant-...)"
    $token = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
    @(
        "UNITYTOOLS_PROVIDER=anthropic",
        "ANTHROPIC_API_KEY=$apiKey",
        "UNITYTOOLS_BRIDGE_TOKEN=$token"
    ) | Set-Content -Path $envFile -Encoding ascii
    Write-Ok ".env olusturuldu (bridge token otomatik uretildi)."
}
if ($token) {
    # Unity paneli ve Python ayni token'i gormeli; kullanici ortamina kalici yaz.
    setx UNITYTOOLS_BRIDGE_TOKEN "$token" | Out-Null
    $env:UNITYTOOLS_BRIDGE_TOKEN = $token
    Write-Ok "UNITYTOOLS_BRIDGE_TOKEN kullanici ortamina yazildi (setx)."
}

# ---------------------------------------------------------------- 5. unity eklentisi
Write-Step "Unity editor eklentisi"
$unitytoolsExe = Join-Path $InstallDir ".venv\Scripts\unitytools.exe"
$unityProject = Read-Host "Unity projenin klasor yolu (bos birakirsan bu adim atlanir)"
if ($unityProject) {
    if (Test-Path (Join-Path $unityProject "Assets")) {
        & $unitytoolsExe install-unity-plugin --project "$unityProject"
        Write-Ok "Eklenti kuruldu. Unity'de proje acikken derlenecek."
    } else {
        Write-Warn2 "'$unityProject' bir Unity projesine benzemiyor (Assets klasoru yok); atlandi."
        Write-Warn2 "Sonra elle calistir: `"$unitytoolsExe`" install-unity-plugin --project `"C:\yol\Proje`""
    }
} else {
    Write-Warn2 "Atlandi. Sonra elle calistir: `"$unitytoolsExe`" install-unity-plugin --project `"C:\yol\Proje`""
}

# ---------------------------------------------------------------- ozet
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  KURULUM TAMAM" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Siradaki adimlar:" -ForegroundColor Cyan
Write-Host "  1. Unity'de projeni ac (eklenti derlensin)"
Write-Host "  2. Chat server'i baslat:"
Write-Host "       cd $InstallDir"
Write-Host "       .\.venv\Scripts\unitytools.exe chat-server --engine unity"
Write-Host "  3. Unity panelinde Connect'e bas"
Write-Host ""
Write-Host "Sorun cikarsa once dogrulama: .\.venv\Scripts\unitytools.exe status"
