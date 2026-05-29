"""Starter content for new studio projects."""
from __future__ import annotations


GDD_TEMPLATE = """# Game Design Document

> One-page tek doğru kaynak. Sistem her gün buraya bakar; burada yazmıyorsa
> "kapsam dışı" sayılır. Kısa tut, link bolca koy.

## 1. Pitch
*Bir cümlede ne tür oyun, kim için, neden eğlenceli?*

## 2. Core Loop
*Oyuncu ne yapar → ne kazanır → niye tekrar yapar?*

## 3. Pillars (3-5 madde)
- ...
- ...
- ...

## 4. Scope
- Hedef oturum süresi:
- Platform:
- Hedef sürüm tarihi:

## 5. Mechanics
*Sistem buraya yeni mekanik eklemek istediğinde önce decisions log'una önerir,
onaylanırsa buraya yazılır.*

## 6. Out of Scope
*Bilinçli olarak yapmadıklarımız. Liste uzadıkça oyun netleşir.*
"""


ART_BIBLE_TEMPLATE = """# Art Bible

## 1. Stil Tanımı
*"PS1 lo-fi", "Studio Ghibli watercolor", "stylized PBR" — referansları yaz.*

## 2. Renk Paleti
| Rol | Hex | Notlar |
|---|---|---|
| Primary | #______ | |
| Secondary | #______ | |
| Accent | #______ | |
| Shadow | #______ | |

## 3. Referans İmgeler
*`studio/refs/` altına koy, buraya link ver.*

- `refs/level_target_01.png` — istediğimiz mood
- `refs/hero_silhouette.png` — karakter siluet hedefi

## 4. Material Kuralları
- Roughness aralığı:
- Metallic kullanımı:
- Tiling tex sınırı:

## 5. Lighting Reçetesi
- Ana ışık tipi:
- Sky / fog:
- Post-process:

## 6. "Yapma" Listesi
*Stil ihlali sayılan şeyler. QA agent buna karşı denetler.*
"""


AUDIO_BRIEF_TEMPLATE = """# Audio Brief

> Ses kimliği tek-sayfa: mood, palet (frekans/timbre), referans
> parçalar, "yapma" listesi. Audio Director burayı sahibi.

## 1. Mood Tanımı
*"Cold synth ambient", "8-bit chiptune", "orchestral cinematic" -
 referans parçaların bir listesi.*

## 2. Sonik Palet
| Rol | Tanım | Notlar |
|---|---|---|
| Ambient bed | (e.g. low pad 60-200 Hz) | |
| Movement / motion | (e.g. high-passed perc 2-6 kHz) | |
| Impact / feedback | (e.g. tonal stinger A4-E5) | |
| UI / feedback | (short, dry, 4-8 kHz) | |

## 3. Referans Parçalar
*`studio/refs/audio/` altına koy ya da YouTube/Spotify linki ver.*

- `refs/audio/menu_loop.wav` - hedef ana menü mood
- "<artist - track>" - belirli bir bridge / drop hedefi

## 4. Implementasyon Kuralları
- Sample rate: 44.1 kHz / 48 kHz
- Bit depth: 16 / 24
- Mix bus: master peak <= -1 dBFS
- 3D vs 2D: hangi sesler spatial?

## 5. "Yapma" Listesi
*Stilistik veto. QA agent karşı denetler.*
- ...
"""


SPRINT_TEMPLATE = """# Current Sprint

> Producer her sabah günceller. Bu hafta için neye odaklandığımız.

## Hedef
*Bu sprintin sonunda ne çalışıyor olacak?*

## Bu Hafta
- [ ] ...

## Riskler / Blokajlar
- ...

## Bu Sprintte Olmayacaklar
- ...
"""


ACHIEVEMENTS_TEMPLATE = """# Achievements

> Achievement Designer maintains. Every unlock the player can earn,
> with its trigger condition + threshold + display copy. The Worker
> reads this list and attaches one Achievement component per row to
> a hidden 'Achievements' GameObject in the play scene.

## Roster

| Key            | Trigger              | Threshold | Unlock Message                |
|----------------|----------------------|-----------|-------------------------------|
| first_blood    | ScoreAtLeast         | 1         | First score!                  |
| collector_10   | ScoreAtLeast         | 10        | 10 collected — getting it.    |
| completionist  | ScoreAtLeast         | (winScore)| All coins!                    |
| close_call     | LivesRemainingAtMost | 1         | Down to your last life...     |
| game_over      | GameOver             | -         | Run complete.                 |

## Design Rules
*Keep additions tight. Each achievement must be:*
- *Discoverable through normal play (no obscure conditions).*
- *Tied to a single GameSession signal (no compound conditions —*
  *the runtime supports one trigger per Achievement component).*
- *Worth showing a toast for — if it would fire silently, drop it.*

## Trigger Kinds
*Match the C# Achievement.TriggerKind enum exactly:*
- `ScoreAtLeast` — fires when `GameSession.Score >= threshold`
- `LivesRemainingAtMost` — fires when `GameSession.Lives <= threshold`
- `GameOver` — fires when `GameSession.IsOver` becomes true
  (threshold is ignored)

## UI Surface
*Where the unlock toast appears + how long it stays. Coordinate
with UI Builder if a new overlay is needed.*
- Default: a 4-second slide-in label at the top-center of the HUD.

## Persistence
*Achievement keys are stored under PlayerPrefs key*
*`unitytools.achievement.<key>`. Unlocks survive scene loads and*
*game sessions. SettingsStore.DeleteKey clears them (new game+).*
"""


SCENE_CATALOG_TEMPLATE = """# Scene Catalog

> Scene Director maintains. The scene-graph of the game — every
> scene the player can land on + how they get there + back. The
> Build Engineer reads this to populate EditorBuildSettings; the
> Worker reads it when wiring LoadSceneOnClick / GameSession
> transitions.

## Scenes

| Path                       | Role            | Loaded by                              | Notes |
|----------------------------|-----------------|----------------------------------------|-------|
| Assets/Scenes/Title.unity  | title screen    | scene 0 (auto-load on launch)          | LoadSceneOnClick -> GameScene |
| Assets/Scenes/Game.unity   | main play loop  | LoadSceneOnClick (Start button)        | GameSession winScene='Win', loseScene='GameOver' |
| Assets/Scenes/Win.unity    | win celebration | GameSession.WinGame()                  | LoadSceneOnClick back to Title |
| Assets/Scenes/GameOver.unity | lose / retry  | GameSession.LoseGame()                 | LoadSceneOnClick back to Title or Game |
| Assets/Scenes/Credits.unity  | credits roll  | LoadSceneOnClick (Title 'Credits' btn) | LoadSceneOnClick back to Title |

## Transitions
*Each row = one allowed transition. Helps the Worker decide what
LoadSceneOnClick.sceneName each button should carry.*
- Title  -> Game        via "Start" button
- Title  -> Credits     via "Credits" button
- Game   -> Win         via GameSession auto-win
- Game   -> GameOver    via GameSession lives==0
- Win    -> Title       via "Return" button
- GameOver -> Game      via "Retry" button
- GameOver -> Title     via "Menu" button
- Credits -> Title      via "Back" button or auto-return

## Build Settings
*All scenes the binary must include. Build Engineer adds them via
unity_add_scene_to_build at scene-catalog approval time.*
- [ ] Assets/Scenes/Title.unity
- [ ] Assets/Scenes/Game.unity
- [ ] Assets/Scenes/Win.unity
- [ ] Assets/Scenes/GameOver.unity
- [ ] Assets/Scenes/Credits.unity

## Persistent State Across Scenes
*What survives scene transitions? SettingsStore is automatic.
DontDestroyOnLoad GameObjects (rare) listed here.*
- SettingsStore: volume, locale, high_score (PlayerPrefs)
- (none persistent GOs unless noted)
"""


TUTORIAL_TEMPLATE = """# Tutorial / Onboarding

> Tutorial Designer maintains. The first 60 seconds a new player
> experiences. The bridge between "they bought / clicked" and
> "they understand the game's core loop."

## Player Goal (one line)
*What is the player trying to do? Steam refunds happen if this isn't
clear within 90 seconds.*

## Controls
*List every key/button the player needs to press to play. Hide deeper
options for later.*
- ...
- ...

## Onboarding Flow (3-5 beats)
*Each beat = one screen / one moment. Tell don't show; show don't
explain at length.*

### Beat 1 — Hook
*First thing the player sees. Should make them want to press a key.*

### Beat 2 — First Action
*Reward the first button press immediately. Coin / hit / movement.*

### Beat 3 — First Choice
*Surface the game's first meaningful decision.*

### Beat 4 (optional) — First Failure
*Let the player lose once on a safe surface. Teach the fail state.*

### Beat 5 — Off Training Wheels
*The HUD is final, the rules are clear. Let them play.*

## UI Surface
*Which Canvas / overlay / text element shows each beat?*
- Beat 1: ...
- Beat 2: ...

## Skip Path
*Every tutorial needs a one-key skip. Document the binding.*
- ...

## Telemetry
*Which events does Playtester log to track tutorial completion?*
- ...
"""


PRESS_KIT_TEMPLATE = """# Press Kit

> Marketing Director maintains. Ship-ready summary for store listings,
> press inquiries, social posts.

## Game Title
*Resmi ad. PlayerSettings.productName ile aynı olmalı.*

## Tagline (one line)
*Tek cümlede pitch. Steam capsule altında görünür.*

## Description (3 paragraphs)
*Paragraph 1: oyunun kalbinde ne var. Paragraph 2: temel mekanik / oyun
deneyimi. Paragraph 3: ton + hedef kitle + müzik / estetik vurgusu.*

## Features (5 bullets)
- ...
- ...
- ...
- ...
- ...

## Hero Shots
*studio/qa/screenshots/ altındaki marketing_* dosyalarına işaret edin.
En az 3 farklı kompozisyon: wide landscape, character closeup, action moment.*

## Credits
- Studio: ...
- Developer: ...
- Sound: ...

## Quotes / Press Mentions
- ...

## Contact + Links
- Email: ...
- Website: ...
- Store page: ...

## Build Targets
*Hangi platformlar shipped: Windows / Mac / Linux / WebGL / mobile.*
"""


GITIGNORE_TEMPLATE = """# Studio runtime artifacts — keep state, ignore large captures.
qa/screenshots/
qa/diffs/
memory/
"""


def starter_files() -> dict[str, str]:
    """Map of relative-path -> content for `studio init`."""
    return {
        "gdd.md": GDD_TEMPLATE,
        "art_bible.md": ART_BIBLE_TEMPLATE,
        "audio_brief.md": AUDIO_BRIEF_TEMPLATE,
        "press_kit.md": PRESS_KIT_TEMPLATE,
        "tutorial.md": TUTORIAL_TEMPLATE,
        "scene_catalog.md": SCENE_CATALOG_TEMPLATE,
        "achievements.md": ACHIEVEMENTS_TEMPLATE,
        "sprint_current.md": SPRINT_TEMPLATE,
        ".gitignore": GITIGNORE_TEMPLATE,
    }
