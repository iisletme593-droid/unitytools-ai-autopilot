# Asset Yeniden Üretim Planı (Thorny Ivy)

> Eski PC'deki .blend kaynakları ve Unity projesi kayboldu. Bu doküman, repodaki
> script referanslarından çıkarılan **eksiksiz asset envanteri** ve her birinin
> yeniden üretim yoludur. Kural: her .blend kaynağı ve export edilen FBX artık
> oyun reposunda versiyonlanır (`scripts/init_game_repo.ps1`).

## Envanter (script referanslarından)

| # | Asset | Referans (kod) | Üretim yolu | Öncelik |
|---|---|---|---|---|
| 1 | Zemin/teren + yol | `SceneBuilder` (Z ekseni yol düzeni) | Unity terrain + `unity_prepare_*` araçları | P0 |
| 2 | Çam ağacı | `SceneBuilder` orman şeridi | Blender: geometry nodes / sapling add-on → FBX | P0 |
| 3 | Köknar ağacı | `SceneBuilder` orman şeridi | Blender (çamın varyantı) | P0 |
| 4 | Yaprak/kabuk materyalleri | `IslandTreePainter` (foliage/bark paleti) | Mevcut script + HF doku üretimi | P0 |
| 5 | Büyük kulübe (köy kapısı sol) | `SceneBuilder` | Blender: modüler kit (duvar/çatı/kiriş) | P0 |
| 6 | Küçük kulübe (köy kapısı sağ) | `SceneBuilder` | Aynı modüler kitten varyant | P0 |
| 7 | Kamp ateşi | `SceneBuilder`, HF `scene_campfire` | Blender odun yığını + Unity VFX (alev/ışık) | P0 |
| 8 | Gotik kale (ince kuleli) | `SceneBuilder` Z=+85 | Blender modüler kit: sur, kule, kapı | P1 |
| 9 | Sihirli ışın (kale tepesi) | `SceneBuilder` | Unity VFX Graph / ışık şaftı | P1 |
| 10 | Oyuncu: savaşçı | HF `character_warrior`, `CharacterModelSwapper` | Blender model VEYA Mixamo gövde + retexture | P0 |
| 11 | Düşman: Brute | HF `character_enemy_brute`, `EnemyAnimatorSetup` | Blender model + Mixamo rig/anim | P0 |
| 12 | Animasyon seti (idle/run/attack/dodge/death) | `MixamoAnimationImporter` | Mixamo (ücretsiz, yeniden indirilebilir) | P0 |
| 13 | Gece skybox | HF `skybox_night`, `GeneratedAssetLoader` | HF üretici (`hf_asset_generator`) | P1 |
| 14 | Orman zemin dokusu | HF `texture_forest_ground` | HF üretici | P1 |
| 15 | Ağaç kabuğu dokusu | HF `texture_tree_bark` | HF üretici | P1 |
| 16 | Sis/atmosfer ayarı | `SceneBuilder` (mavi-gri sis) | HDRP volumetric fog — script kuruyor | P0 |

## Üretim sırası (önerilen)

**Hafta 1 — "gri kutudan yeşil ormana":**
1. `setup_unity_project.ps1` ile proje + eklenti (yapıldıysa atla)
2. `init_game_repo.ps1` ile projeyi git'e al ← **her şeyden önce**
3. Blender 5.1 kur (`setup_windows.ps1` artık kuruyor)
4. P0 ağaçlar + kulübeler + kamp ateşi: Blender'da üret → `scripts/blender/export_fbx.py`
   ile FBX → projeye al → `SceneBuilder` sahneyi kursun
5. Mixamo savaşçı + Brute + animasyon seti → `MixamoAnimationImporter`

**Hafta 2 — dövüş dilimi:**
6. Dövüş kontrolcüsü (dodge/stamina/lock-on) — `docs/GAME_DESIGN.md` dilim 1
7. Kale (P1) + skybox/dokular (HF hattı) + atmosfer cilası

## Notlar

- Autopilot panelinden "Thorny Ivy sahnesini kur" benzeri komutlar `SceneBuilder`'ı
  tetikler; asset isimleri script'lerin beklediği adlarla eşleşmeli (ör. ağaçlar
  `Nature_Trees_*` önekiyle aranıyor — `IslandTreePainter` foliage/bark tespiti
  isim anahtar kelimeleriyle çalışır).
- HF doku hattı manifest yolu: `output/unity/generated_assets_manifest.json`
  (`GeneratedAssetLoader` Tools > Autopilot > Load Generated Assets).
