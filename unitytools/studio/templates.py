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
        "sprint_current.md": SPRINT_TEMPLATE,
        ".gitignore": GITIGNORE_TEMPLATE,
    }
