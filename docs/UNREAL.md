# Unreal Engine Support / Unreal Engine Destegi

UnityTools AI Autopilot v2.7 adds an Unreal Engine bridge and an embedded Unreal Editor chat tab.

UnityTools AI Autopilot v2.7 ile Unreal Engine bridge ve Unreal Editor icinde gomulu chat sekmesi gelir.

## What Works

- Native Unreal Editor tab: `Tools > UnrealTools > Open UnrealTools AI Chat`
- Unreal Python bridge on `127.0.0.1:8777`
- Embedded chat core on `127.0.0.1:7778` with `--engine unreal`
- Actor listing, semantic actor search, actor spawn/delete/transform
- `/Game` asset catalog and semantic asset search
- Unity source asset staging and Unreal import pipeline
- Resume manifest for long imports
- Safe static FBX import mode to avoid broken skeletal/animation stalls

## Kurulum

```powershell
pip install -e .
unitytools install-unreal-plugin --project "C:\Path\To\Project\Project.uproject"
```

Open or restart Unreal Editor. The plugin enables these dependencies in the `.uproject`:

- `UnrealToolsBridge`
- `PythonScriptPlugin`
- `EditorScriptingUtilities`

Then test:

```powershell
unitytools unreal-ping
unitytools doctor
```

## Editor Chat

Inside Unreal:

```text
Unreal opens the panel automatically after startup.
Unreal acilistan sonra paneli otomatik acar.

UnrealTools AI > Open UnrealTools AI Chat
Tools > UnrealTools > Open UnrealTools AI Chat
Window > UnrealTools > Open UnrealTools AI Chat
```

If your Unreal layout/language does not show the `Tools` menu, use `Window > UnrealTools` instead. The tab is also registered as a normal dockable tab named `UnrealTools AI Chat`.

Use `Core Baslat`, then `Baglan`. The panel starts:

```powershell
python -m unitytools.cli.entry chat-server --use-dual-agent --engine unreal
```

The `--engine unreal` hint tells the model to prefer `unreal_*` tools instead of Unity tools.

## Unity Asset Migration To Unreal

Stage Unity source assets:

```powershell
unitytools migrate-unity-assets-to-unreal \
  --unity-project "C:\Path\To\UnityProject" \
  --staging "D:\UnityToolsV2\UnrealMigrationStaging"
```

Import into Unreal while Unreal Editor is open:

```powershell
unitytools migrate-unity-assets-to-unreal \
  --unity-project "C:\Path\To\UnityProject" \
  --staging "D:\UnityToolsV2\UnrealMigrationStaging" \
  --import-into-unreal \
  --category-folders \
  --replace-existing \
  --import-mode safe_static \
  --batch-size 25
```

For smaller chunks:

```powershell
unitytools migrate-unity-assets-to-unreal \
  --unity-project "C:\Path\To\UnityProject" \
  --staging "D:\UnityToolsV2\UnrealMigrationStaging" \
  --import-into-unreal \
  --category-folders \
  --import-limit 25
```

The migration writes a resume manifest:

```text
UnrealMigrationStaging/unreal_import_manifest.json
```

If Unreal closes or an importer fails, run the same command again. Imported files are skipped automatically. Failed files are skipped unless you pass `--retry-failed`.

## Important Limits

Unity scenes, prefabs, C# scripts, Unity materials, and Animator Controllers do not convert 1:1 into Unreal. The migration focuses on portable source assets:

- FBX, OBJ, GLB, GLTF
- PNG, JPG, TGA, TIFF, EXR
- WAV, MP3

Some GLB/FBX files from Sketchfab or generated tools may have invalid skeletons, bad material references, duplicate names, or huge Nanite build cost. Use `safe_static` first. Convert/rebuild failed assets later if needed.

## Turkish Notes / Turkce Notlar

- Unity prefab/script/material dosyalari Unreal'a birebir donusmez.
- Mesh, texture ve audio dosyalari otomatik tasinir.
- Buyuk GLB/FBX assetleri Unreal import sirasinda uzun sure Nanite/static mesh build yapabilir.
- Import yarida kesilirse ayni komutu tekrar calistir; manifest kaldigi yerden devam eder.
- Bozuk dosyalar `failed` listesine yazilir, tum sistemi durdurmaz.
