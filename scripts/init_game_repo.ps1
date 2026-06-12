# Oyun projesini git'e al - "bir daha asla kaybetmeyecegiz" scripti
#
# Tek satirla calistir:
#   irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/claude/beautiful-franklin-llxce2/scripts/init_game_repo.ps1 | iex
#
# Yaptiklari:
#   1. C:\dev\UnityProje icinde git deposu baslatir
#   2. Unity icin dogru .gitignore + buyuk binary'ler icin .gitattributes (Git LFS) yazar
#   3. .blend kaynak klasoru (BlenderAssets) olusturur - Blender dosyalari da versiyonlanir
#   4. Ilk commit'i atar
#   5. GitHub'a baglamak icin komutlari gosterir (push icin tarayici girisi yeterli)

$ErrorActionPreference = "Continue"
$ProjectPath = "C:\dev\UnityProje"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }

if (-not (Test-Path (Join-Path $ProjectPath "Assets"))) {
    throw "Unity projesi bulunamadi: $ProjectPath. Once setup_unity_project.ps1 calistir."
}

Write-Step "Git deposu hazirlaniyor: $ProjectPath"
if (Test-Path (Join-Path $ProjectPath ".git")) {
    Write-Ok "Proje zaten git'te; ayarlar tazelenecek."
} else {
    git -C $ProjectPath init
    if ($LASTEXITCODE -ne 0) { throw "git init basarisiz." }
    Write-Ok "git init tamam."
}

# ------------------------------------------------------------ .gitignore
$gitignore = @"
# Unity uretilen klasorler (Library yeniden uretilir, ASLA commit edilmez)
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
MemoryCaptures/

# Unity uretilen dosyalar
*.csproj
*.sln
*.suo
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db
crashlytics-build.properties

# Blender yedekleri (kaynak .blend COMMIT EDILIR, yedekler edilmez)
*.blend1
*.blend2

# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
"@
Set-Content -Path (Join-Path $ProjectPath ".gitignore") -Value $gitignore -Encoding ascii
Write-Ok ".gitignore yazildi (Library haric her sey versiyonlanir; .blend DAHIL)."

# ------------------------------------------------------------ Git LFS
Write-Step "Buyuk dosyalar icin Git LFS"
git -C $ProjectPath lfs install 2>$null
if ($LASTEXITCODE -eq 0) {
    $gitattributes = @"
*.blend filter=lfs diff=lfs merge=lfs -text
*.fbx filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
"@
    Set-Content -Path (Join-Path $ProjectPath ".gitattributes") -Value $gitattributes -Encoding ascii
    Write-Ok "LFS aktif: blend/fbx/doku/ses dosyalari LFS uzerinden saklanacak."
} else {
    Write-Warn2 "Git LFS bulunamadi; binary'ler normal git'le saklanacak (calisir ama repo buyur)."
}

# ------------------------------------------------------------ Blender kaynak klasoru
$blenderDir = Join-Path $ProjectPath "BlenderAssets"
if (-not (Test-Path $blenderDir)) {
    New-Item -ItemType Directory -Path $blenderDir | Out-Null
    Set-Content -Path (Join-Path $blenderDir "README.md") -Value @"
# BlenderAssets

Oyunun .blend kaynak dosyalari BURADA tutulur ve git'e COMMIT EDILIR.
(Eski PC'de bu yapilmadigi icin tum assetler kaybolmustu - bir daha asla.)

Akis: .blend kaydet -> scripts/blender/export_fbx.py ile FBX'i Assets/ altina ver
-> commit + push.
"@ -Encoding utf8
    Write-Ok "BlenderAssets/ klasoru olusturuldu (.blend kaynaklari icin)."
}

# ------------------------------------------------------------ ilk commit
Write-Step "Ilk commit"
git -C $ProjectPath add -A
git -C $ProjectPath -c user.name="ThornyIvy" -c user.email="dev@thornyivy.local" commit -m "Initial commit: Unity project under version control from day one"
if ($LASTEXITCODE -eq 0) { Write-Ok "Ilk commit atildi." }
else { Write-Warn2 "Commit atilamadi (degisiklik yok ya da kimlik ayari gerekli olabilir)." }

# ------------------------------------------------------------ ozet
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host "  OYUN PROJESI ARTIK GIT'TE" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "GitHub'a baglamak icin (onerilir - yedek bulutta olsun):" -ForegroundColor Cyan
Write-Host "  1. https://github.com/new adresinde 'thorny-ivy' adinda PRIVATE repo ac"
Write-Host "  2. Sonra:"
Write-Host "       cd $ProjectPath"
Write-Host "       git remote add origin https://github.com/KULLANICI_ADIN/thorny-ivy.git"
Write-Host "       git push -u origin master"
Write-Host "     (Push sirasinda tarayici acilir, GitHub girisi yeterli.)"
Write-Host ""
Write-Host "Gunluk aliskanlik: is bitiminde  git add -A; git commit -m 'gun sonu'; git push"
