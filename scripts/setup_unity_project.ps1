# UnityTools - sifirdan Unity projesi olustur + eklentiyi kur + her seyi baslat
#
# Tek satirla calistir (once setup_windows.ps1 calismis olmali):
#   irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/claude/beautiful-franklin-llxce2/scripts/setup_unity_project.ps1 | iex
#
# Yaptiklari:
#   1. Kurulu Unity Editor'u bulur (Hub varsayilan klasoru, ikincil klasor, eski tip kurulum)
#      - Hic editor yoksa Unity Hub'i winget ile kurar ve LTS kurulumu icin yonlendirir
#   2. C:\dev\UnityProje yoksa Unity'nin -createProject komutuyla SIFIRDAN olusturur (GUI acilmaz)
#   3. UnityTools eklentisini projeye kurar
#   4. Unity'yi projeyle baslatir + chat-server'i ayri pencerede acar -> panelde Connect'e basman yeterli

$ErrorActionPreference = "Continue"

$InstallDir   = "C:\dev\unitytools-ai-autopilot"
$ProjectPath  = "C:\dev\UnityProje"
$unitytoolsExe = Join-Path $InstallDir ".venv\Scripts\unitytools.exe"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

if (-not (Test-Path $unitytoolsExe)) {
    throw "unitytools bulunamadi ($unitytoolsExe). Once kurulum scriptini calistir: setup_windows.ps1"
}

# ---------------------------------------------------------- 1. Unity Editor bul
Write-Step "Unity Editor araniyor"

function Find-UnityEditors {
    $exes = New-Object System.Collections.Generic.List[string]
    $roots = New-Object System.Collections.Generic.List[string]
    $roots.Add("$env:ProgramFiles\Unity\Hub\Editor")
    # Hub'in ikincil kurulum klasoru (kullanici degistirmis olabilir)
    $secondary = Join-Path $env:APPDATA "UnityHub\secondaryInstallPath.json"
    if (Test-Path $secondary) {
        try {
            $p = (Get-Content $secondary -Raw).Trim().Trim('"')
            if ($p) { $roots.Add($p) }
        } catch { }
    }
    foreach ($root in $roots) {
        if (Test-Path $root) {
            Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $exe = Join-Path $_.FullName "Editor\Unity.exe"
                if (Test-Path $exe) { $exes.Add($exe) }
            }
        }
    }
    # Eski tip (Hub'siz) kurulum
    $legacy = "$env:ProgramFiles\Unity\Editor\Unity.exe"
    if (Test-Path $legacy) { $exes.Add($legacy) }
    return $exes
}

$editors = Find-UnityEditors
if (-not $editors -or $editors.Count -eq 0) {
    Write-Warn2 "Kurulu Unity Editor bulunamadi."
    if (-not (Test-Path "$env:ProgramFiles\Unity Hub\Unity Hub.exe")) {
        Write-Step "Unity Hub winget ile kuruluyor"
        winget install --id Unity.UnityHub -e --source winget --accept-package-agreements --accept-source-agreements
    }
    Write-Host ""
    Write-Host "Simdi tek manuel adim kaldi:" -ForegroundColor Cyan
    Write-Host "  1. Acilan Unity Hub'da oturum ac (Unity hesabi gerekli, ucretsiz)"
    Write-Host "  2. Installs -> Install Editor -> en ustteki LTS surumu sec -> Install"
    Write-Host "  3. Kurulum bitince BU KOMUTU TEKRAR calistir; gerisini ben hallederim."
    Start-Process "$env:ProgramFiles\Unity Hub\Unity Hub.exe" -ErrorAction SilentlyContinue
    exit 1
}

# En yuksek surumu sec (klasor adi surumdur: 6000.0.32f1 gibi)
$unityExe = $editors | Sort-Object {
    $v = Split-Path (Split-Path $_ -Parent) -Parent | Split-Path -Leaf
    try { [version]($v -replace "[fab].*$", "") } catch { [version]"0.0" }
} -Descending | Select-Object -First 1
Write-Ok "Unity Editor: $unityExe"

# ---------------------------------------------------------- 2. proje olustur
Write-Step "Unity projesi hazirlaniyor: $ProjectPath"
$isProject = (Test-Path (Join-Path $ProjectPath "Assets")) -and
             (Test-Path (Join-Path $ProjectPath "ProjectSettings\ProjectVersion.txt"))
if ($isProject) {
    Write-Ok "Proje zaten var, olusturma atlandi."
} else {
    Write-Warn2 "Proje sifirdan olusturuluyor (GUI acilmaz, ilk seferde birkac dakika surebilir)..."
    $log = Join-Path $env:TEMP "unity_create_project.log"
    $proc = Start-Process -FilePath $unityExe -ArgumentList @(
        "-batchmode", "-quit", "-createProject", "`"$ProjectPath`"", "-logFile", "`"$log`""
    ) -PassThru -Wait
    $created = (Test-Path (Join-Path $ProjectPath "Assets")) -and
               (Test-Path (Join-Path $ProjectPath "ProjectSettings\ProjectVersion.txt"))
    if (-not $created) {
        Write-Warn2 "Proje olusturulamadi (exit: $($proc.ExitCode)). Log: $log"
        throw "Unity -createProject basarisiz. Logun son satirlarini bana gonder: Get-Content `"$log`" -Tail 30"
    }
    Write-Ok "Proje olusturuldu."
}

# ---------------------------------------------------------- 3. eklenti kur
Write-Step "UnityTools eklentisi projeye kuruluyor"
& $unitytoolsExe install-unity-plugin --project "$ProjectPath"
if ($LASTEXITCODE -ne 0) { throw "install-unity-plugin basarisiz; cikti yukarida." }
Write-Ok "Eklenti kuruldu."

# ---------------------------------------------------------- 4. baslat
Write-Step "Unity ve chat-server baslatiliyor"
Start-Process -FilePath $unityExe -ArgumentList @("-projectPath", "`"$ProjectPath`"")
Write-Ok "Unity aciliyor (ilk acilis + eklenti derlemesi birkac dakika surebilir)."

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd `"$InstallDir`"; .\.venv\Scripts\unitytools.exe chat-server --engine unity"
)
Write-Ok "Chat server ayri pencerede baslatildi."

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  HER SEY HAZIR" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Son adim:" -ForegroundColor Cyan
Write-Host "  Unity acilip eklenti derlendikten sonra ust menuden:"
Write-Host "    Tools > UnityTools > Open AI Autopilot"
Write-Host "  panelini ac ve Connect'e bas. Hepsi bu."
