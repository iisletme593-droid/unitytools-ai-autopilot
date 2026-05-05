# Unity Editor Embedded Chat Guide

UnityTools AI is designed to feel like a native Unity Editor tool.

UnityTools AI, Unity Editor'in kendi araci gibi hissettirecek sekilde tasarlanmistir.

Open it from:

```text
Window > UnityTools AI > Autopilot Chat
```

or:

```text
Tools > UnityTools > Open AI Autopilot
```

## How It Works

The Editor panel starts the Python chat core silently in the background. You do not need to open a terminal for normal chat usage.

Editor paneli Python chat core'u arka planda sessizce baslatir. Normal chat kullanimi icin terminal acman gerekmez.

Flow:

```text
UnityTools AI panel
  -> Python chat core on port 7778
  -> model provider: Ollama or Anthropic
  -> tool call
  -> Unity command bridge on port 7777
  -> scene changes in the Editor
```

## Toolbar

- `Connect`: connect to the embedded AI core
- `Restart Core`: restart the Python chat server owned by the panel
- `Auto`: automatically start/connect when the window opens
- `Clear`: clear UI history and reset chat memory
- `Log`: reveal the embedded core log file
- `Settings`: configure host, port, command, and arguments

## Recommended Local Provider

## Onerilen Lokal Provider

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:14b-instruct
```

Install the model / Modeli indir:

```powershell
ollama pull qwen2.5:14b-instruct
```

## Example Prompts

## Ornek Promptlar

```text
List the active scene objects.
Aktif sahnedeki objeleri listele.
Create 5 cubes along the X axis.
X ekseninde 5 kup olustur.
real relis realist tree assetlerini bul, sahneye koyma, sadece en iyi 5 tanesini listele.
Gercek tree assetlerinden kucuk bir orman yap.
Move Player_Start to x=0 y=1 z=0.
Export Assets/Source/Barbar.blend as an FBX and import it under Models.
```

## Troubleshooting

If the panel says AI Offline:

1. Click `Restart Core`.
2. Click `Log` and read the Python error.
3. Run `unitytools doctor` from the project folder.

If Unity commands do not run:

1. Open `Tools > UnityTools > Bridge Status`.
2. Start the Unity bridge if needed.
3. Run `unitytools unity-ping`.

If Ollama is offline:

```powershell
ollama serve
ollama pull qwen2.5:14b-instruct
unitytools doctor
```

