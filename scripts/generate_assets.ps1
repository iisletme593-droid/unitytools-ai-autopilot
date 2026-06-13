# Thorny Ivy - P0 asset'lerini uret ve Unity projesine yerlestir
#
# Tek satirla calistir:
#   irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/claude/beautiful-franklin-llxce2/scripts/generate_assets.ps1 | iex
#
# Yaptiklari:
#   1. Blender'i bulur (yoksa winget ile kurar)
#   2. generate_p0_assets.py'yi headless calistirir:
#      - 12 GLB -> C:\dev\UnityProje\Assets\FantasyRPG  (SceneBuilder'in aradigi adlarla)
#      - kaynak galeri -> C:\dev\UnityProje\BlenderAssets\p0_assets.blend
#   3. Oyun reposu git'teyse uretilen asset'leri commit'ler

$ErrorActionPreference = "Continue"

$InstallDir  = "C:\dev\unitytools-ai-autopilot"
$ProjectPath = "C:\dev\UnityProje"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

# Once arac reposunu guncelle - uretici script son push'la gelmis olabilir.
Write-Step "Arac reposu guncelleniyor"
if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
    throw "Repo bulunamadi: $InstallDir. Once setup_windows.ps1 calistir."
}
git -C $InstallDir fetch origin
$curBranch = git -C $InstallDir rev-parse --abbrev-ref HEAD
git -C $InstallDir pull --ff-only origin $curBranch
Write-Ok "Repo guncel: $(git -C $InstallDir log -1 --format='%h %s')"

$genScript = Join-Path $InstallDir "scripts\blender\generate_p0_assets.py"
if (-not (Test-Path $genScript)) { throw "Uretici script hala yok: $genScript. Dal dogru mu? (beklenen: claude/beautiful-franklin-llxce2)" }
if (-not (Test-Path (Join-Path $ProjectPath "Assets"))) {
    throw "Unity projesi bulunamadi: $ProjectPath. Once setup_unity_project.ps1 calistir."
}

# ---------------------------------------------------------------- 1. blender
Write-Step "Blender araniyor"
$blender = Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $blender) {
    Write-Warn2 "Blender yok, winget ile kuruluyor..."
    winget install --id BlenderFoundation.Blender -e --source winget --accept-package-agreements --accept-source-agreements
    $blender = Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $blender) { throw "Blender kurulamadi. blender.org'dan elle kur ve tekrar dene." }
}
Write-Ok "Blender: $($blender.FullName)"

# ---------------------------------------------------------------- 2. uretim
Write-Step "P0 asset'leri uretiliyor (12 adet, ~1 dk)"
$outDir   = Join-Path $ProjectPath "Assets\FantasyRPG"
$blendOut = Join-Path $ProjectPath "BlenderAssets\p0_assets.blend"

# Eski GLB denemesi kalmissa temizle: Unity GLB'yi paketsiz okuyamiyor ve
# ayni isimli GLB+FBX isim aramasini karistirir.
Get-ChildItem (Join-Path $outDir "*.glb") -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem (Join-Path $outDir "*.glb.meta") -ErrorAction SilentlyContinue | Remove-Item -Force

& $blender.FullName --background --factory-startup --python $genScript -- --out "$outDir" --blend "$blendOut"
if ($LASTEXITCODE -ne 0) { throw "Blender uretimi basarisiz (exit $LASTEXITCODE); cikti yukarida." }

$fbxs = Get-ChildItem (Join-Path $outDir "*.fbx") -ErrorAction SilentlyContinue
Write-Ok "$($fbxs.Count) FBX uretildi -> $outDir"
$fbxs | ForEach-Object { Write-Host "      $($_.Name)" }

# ---------------------------------------------------------------- 3. commit
if (Test-Path (Join-Path $ProjectPath ".git")) {
    Write-Step "Oyun reposuna commit'leniyor"
    git -C $ProjectPath add -A
    git -C $ProjectPath -c user.name="ThornyIvy" -c user.email="dev@thornyivy.local" commit -m "Add procedurally generated P0 assets (trees, campfire, rocks, props)"
    if ($LASTEXITCODE -eq 0) { Write-Ok "Commit atildi." } else { Write-Warn2 "Commit atlanamadi/atlandi." }
} else {
    Write-Warn2 "Oyun projesi git'te degil - once init_game_repo.ps1 calistirmani oneririm."
}

# ---------------------------------------------------------------- ozet
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  ASSET'LER HAZIR" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Simdi:" -ForegroundColor Cyan
Write-Host "  1. Unity'yi ac (proje: $ProjectPath) - GLB'ler iceri alinacak"
Write-Host "  2. SceneBuilder sahneyi bu asset'lerle kurar (Tools menusunden de tetiklenebilir)"
Write-Host "  3. Asset'lere bakmak istersen: Blender'da $blendOut"
