# UnityTools - Unity projesini otomatik bul ve editor eklentisini kur
#
# Tek satirla calistir (once setup_windows.ps1 calismis olmali):
#   irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/claude/beautiful-franklin-llxce2/scripts/install_plugin_auto.ps1 | iex
#
# Proje arama sirasi:
#   1. Unity Editor'un "son acilan projeler" kaydi (HKCU registry)
#   2. Unity Hub'in varsayilan proje klasoru (%APPDATA%\UnityHub\projectDir.json)
#   3. Yaygin konumlar: Belgeler, Masaustu, C:\dev, C:\Unity*, D:\ (tek seviye)
# Birden fazla proje bulunursa en son kullanilani secer, digerlerini listeler.

$ErrorActionPreference = "Continue"

$InstallDir = "C:\dev\unitytools-ai-autopilot"
$unitytoolsExe = Join-Path $InstallDir ".venv\Scripts\unitytools.exe"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

if (-not (Test-Path $unitytoolsExe)) {
    throw "unitytools bulunamadi ($unitytoolsExe). Once kurulum scriptini calistir: setup_windows.ps1"
}

function Test-UnityProject($p) {
    if (-not $p) { return $false }
    (Test-Path (Join-Path $p "Assets")) -and (Test-Path (Join-Path $p "ProjectSettings\ProjectVersion.txt"))
}

Write-Step "Unity projeleri araniyor"
$candidates = New-Object System.Collections.Generic.List[string]

# 1) Unity Editor'un son acilan projeleri (registry, REG_BINARY UTF-8 yol tutar)
$utRoot = "HKCU:\Software\Unity Technologies"
if (Test-Path $utRoot) {
    Get-ChildItem $utRoot -ErrorAction SilentlyContinue |
        Where-Object { $_.PSChildName -like "Unity Editor*" } |
        ForEach-Object {
            $props = (Get-ItemProperty $_.PSPath).PSObject.Properties |
                Where-Object { $_.Name -like "RecentlyUsedProjectPaths*" }
            foreach ($prop in $props) {
                $v = $prop.Value
                if ($v -is [byte[]]) { $v = [Text.Encoding]::UTF8.GetString($v).Trim([char]0) }
                if ($v) { $candidates.Add(([string]$v).Trim()) }
            }
        }
}

# 2) Unity Hub varsayilan proje klasorunun altindakiler
$hubJson = Join-Path $env:APPDATA "UnityHub\projectDir.json"
if (Test-Path $hubJson) {
    try {
        $dir = (Get-Content $hubJson -Raw | ConvertFrom-Json).directoryPath
        if ($dir -and (Test-Path $dir)) {
            Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue |
                ForEach-Object { $candidates.Add($_.FullName) }
        }
    } catch { }
}

# 3) Yaygin konumlar (tek seviye tarama)
$roots = @("$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop", "C:\dev", "D:\") +
         (Get-ChildItem "C:\" -Directory -Filter "Unity*" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
foreach ($root in $roots) {
    if (Test-Path $root) {
        Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { $candidates.Add($_.FullName) }
    }
}

# Dogrula + tekillestir
$valid = $candidates |
    Where-Object { Test-UnityProject $_ } |
    ForEach-Object { (Resolve-Path $_ -ErrorAction SilentlyContinue).Path } |
    Where-Object { $_ } |
    Sort-Object -Unique

if (-not $valid) {
    Write-Warn2 "Hic Unity projesi bulunamadi."
    Write-Host ""
    Write-Host "Yapman gereken:" -ForegroundColor Cyan
    Write-Host "  1. Unity Hub'i ac -> New project -> 3D (URP/HDRP fark etmez) -> Create"
    Write-Host "  2. Proje acildiktan sonra bu komutu TEKRAR calistir."
    Write-Host ""
    Write-Host "Ya da yolu biliyorsan elle kur:"
    Write-Host "  `"$unitytoolsExe`" install-unity-plugin --project `"C:\yol\Projen`""
    exit 1
}

# En son kullanilani sec (ProjectSettings yazma zamanina gore)
$chosen = $valid |
    Sort-Object { (Get-Item (Join-Path $_ "ProjectSettings\ProjectVersion.txt")).LastWriteTime } -Descending |
    Select-Object -First 1

Write-Ok "Bulunan proje(ler):"
foreach ($p in $valid) {
    $mark = if ($p -eq $chosen) { " <== SECILDI" } else { "" }
    Write-Host "      $p$mark"
}

Write-Step "Eklenti kuruluyor: $chosen"
& $unitytoolsExe install-unity-plugin --project "$chosen"
if ($LASTEXITCODE -ne 0) { throw "install-unity-plugin basarisiz oldu; cikti yukarida." }

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  EKLENTI KURULDU" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Siradaki adimlar:" -ForegroundColor Cyan
Write-Host "  1. Unity'de bu projeyi ac (eklenti derlenecek):"
Write-Host "       $chosen"
Write-Host "  2. Chat server'i baslat:"
Write-Host "       cd $InstallDir"
Write-Host "       .\.venv\Scripts\unitytools.exe chat-server --engine unity"
Write-Host "  3. Unity menusunde UnityTools panelini ac ve Connect'e bas"
Write-Host ""
Write-Host "Yanlis proje secildiyse dogrusunu elle kur:"
Write-Host "  `"$unitytoolsExe`" install-unity-plugin --project `"C:\dogru\yol`""
