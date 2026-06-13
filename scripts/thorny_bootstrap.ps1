# Thorny Ivy - tum kurulumu KULLANICININ GERCEK projesine yap
#
# Calistir:
#   powershell -ExecutionPolicy Bypass -File C:\dev\unitytools-ai-autopilot\scripts\thorny_bootstrap.ps1
#   (istege bagli: -ProjectPath "C:\yol\Projem" ile elle proje secimi)
#
# Yaptiklari:
#   1. Arac reposunu gunceller
#   2. Unity projesini OTOMATIK bulur:
#      - icinde *Thorn* gecen .unity sahnesi olan proje TERCIH edilir
#      - yoksa en son kullanilan gecerli proje secilir
#   3. UnityTools eklentisini O projeye kurar  -> "Tools" menusu gelir
#   4. P0 asset'lerini (12 FBX) O projeye uretir
#   5. O projeyi git'e alir (yoksa) - .blend kaynaklari dahil
#
# Sonra: Unity'de projeyi ac/odakla -> derleme biter -> Tools > Autopilot > 3 - Full Setup

param([string]$ProjectPath = "")

$ErrorActionPreference = "Continue"
$InstallDir = "C:\dev\unitytools-ai-autopilot"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

function Test-UnityProject($p) {
    if (-not $p) { return $false }
    (Test-Path (Join-Path $p "Assets")) -and (Test-Path (Join-Path $p "ProjectSettings\ProjectVersion.txt"))
}

# ---------------------------------------------------------------- 0. repo guncel
Write-Step "Arac reposu guncelleniyor"
if (-not (Test-Path (Join-Path $InstallDir ".git"))) { throw "Repo yok: $InstallDir (setup_windows.ps1 once)." }
git -C $InstallDir fetch origin | Out-Null
git -C $InstallDir pull --ff-only origin (git -C $InstallDir rev-parse --abbrev-ref HEAD) | Out-Null
Write-Ok "Repo: $(git -C $InstallDir log -1 --format='%h %s')"

$unitytoolsExe = Join-Path $InstallDir ".venv\Scripts\unitytools.exe"
if (-not (Test-Path $unitytoolsExe)) { throw "unitytools kurulu degil (setup_windows.ps1 once)." }

# ---------------------------------------------------------------- 1. proje bul
if (-not $ProjectPath) {
    Write-Step "Unity projeleri taraniyor"
    $candidates = New-Object System.Collections.Generic.List[string]

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
    $hubJson = Join-Path $env:APPDATA "UnityHub\projectDir.json"
    if (Test-Path $hubJson) {
        try {
            $dir = (Get-Content $hubJson -Raw | ConvertFrom-Json).directoryPath
            if ($dir -and (Test-Path $dir)) {
                Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue | ForEach-Object { $candidates.Add($_.FullName) }
            }
        } catch { }
    }
    foreach ($root in @("$env:USERPROFILE", "$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop", "$env:USERPROFILE\Documents\Unity Projects", "C:\dev", "D:\")) {
        if (Test-Path $root) {
            Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | ForEach-Object { $candidates.Add($_.FullName) }
        }
    }

    $valid = $candidates | Where-Object { Test-UnityProject $_ } |
        ForEach-Object { (Resolve-Path $_ -ErrorAction SilentlyContinue).Path } |
        Where-Object { $_ } | Sort-Object -Unique
    if (-not $valid) { throw "Hic Unity projesi bulunamadi. -ProjectPath ile elle ver." }

    # Icinde *Thorn* sahnesi olan proje oncelikli (kullanicinin gercek projesi)
    $thorny = @()
    foreach ($p in $valid) {
        $scene = Get-ChildItem (Join-Path $p "Assets") -Recurse -Filter "*.unity" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "Thorn" } | Select-Object -First 1
        if ($scene) { $thorny += $p; Write-Ok "Thorn sahnesi bulundu: $($scene.Name)  ->  $p" }
    }
    $pool = if ($thorny.Count -gt 0) { $thorny } else { $valid }
    $ProjectPath = $pool | Sort-Object {
        (Get-Item (Join-Path $_ "ProjectSettings\ProjectVersion.txt")).LastWriteTime
    } -Descending | Select-Object -First 1

    Write-Ok "Secilen proje: $ProjectPath"
    foreach ($p in $valid) { if ($p -ne $ProjectPath) { Write-Host "      (diger: $p)" } }
} elseif (-not (Test-UnityProject $ProjectPath)) {
    throw "'$ProjectPath' gecerli bir Unity projesi degil."
}

# ---------------------------------------------------------------- 2. eklenti
Write-Step "UnityTools eklentisi kuruluyor (Tools menusu icin)"
& $unitytoolsExe install-unity-plugin --project "$ProjectPath"
if ($LASTEXITCODE -ne 0) { throw "install-unity-plugin basarisiz." }
Write-Ok "Eklenti kuruldu."

# ---------------------------------------------------------------- 3. asset'ler
Write-Step "P0 asset'leri uretiliyor"
$blender = Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $blender) {
    winget install --id BlenderFoundation.Blender -e --source winget --accept-package-agreements --accept-source-agreements
    $blender = Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $blender) { throw "Blender kurulamadi." }
}
$outDir   = Join-Path $ProjectPath "Assets\FantasyRPG"
$blendOut = Join-Path $ProjectPath "BlenderAssets\p0_assets.blend"
Get-ChildItem (Join-Path $outDir "*.glb") -ErrorAction SilentlyContinue | Remove-Item -Force
& $blender.FullName --background --factory-startup --python (Join-Path $InstallDir "scripts\blender\generate_p0_assets.py") -- --out "$outDir" --blend "$blendOut"
if ($LASTEXITCODE -ne 0) { throw "Blender uretimi basarisiz." }
$fbxs = Get-ChildItem (Join-Path $outDir "*.fbx") -ErrorAction SilentlyContinue
Write-Ok "$($fbxs.Count) FBX -> $outDir"

# ---------------------------------------------------------------- 4. git
Write-Step "Proje git'e aliniyor"
if (-not (Test-Path (Join-Path $ProjectPath ".git"))) {
    git -C $ProjectPath init | Out-Null
    @"
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
*.csproj
*.sln
*.blend1
*.blend2
.DS_Store
"@ | Set-Content -Path (Join-Path $ProjectPath ".gitignore") -Encoding ascii
    git -C $ProjectPath lfs install 2>$null
    if ($LASTEXITCODE -eq 0) {
        @"
*.blend filter=lfs diff=lfs merge=lfs -text
*.fbx filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
"@ | Set-Content -Path (Join-Path $ProjectPath ".gitattributes") -Encoding ascii
    }
}
git -C $ProjectPath add -A
git -C $ProjectPath -c user.name="ThornyIvy" -c user.email="dev@thornyivy.local" commit -m "Bootstrap: UnityTools plugin + P0 assets" | Out-Null
Write-Ok "Commit atildi (veya degisiklik yoktu)."

# ---------------------------------------------------------------- ozet
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  PROJE HAZIR: $ProjectPath" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Simdi:" -ForegroundColor Cyan
Write-Host "  1. Unity'de BU projeyi ac (aciksa pencereye odaklan - yeniden derlenir)"
Write-Host "  2. Derleme bitince ust menu:  Tools > Autopilot > 3 - Full Setup"
Write-Host "  3. Tools menusu HALA yoksa: Console'daki kirmizi hatalari bana gonder."
