# THORNY IVY — Oyun Tasarım Dokümanı (v1.0)

> Bu doküman oyunun kalıcı hafızasıdır — vizyon değişiklikleri buraya işlenir.
> Kaynaklar: kullanıcının tarifi + repodaki hayatta kalan sahne DNA'sı
> (`SceneBuilder.cs v4`). Temel kararlar 2026-06-12'de kullanıcı tarafından
> onaylandı (aşağıda KARAR olarak işaretli).

## Tek cümle

Koyu gotik bir fantezi dünyasında geçen, **tepeden bakışlı** aksiyon-RPG:
Knight Online ruhunda yakın dövüş ve **efsane combo sistemi**, V-Rising'in
kamera/kontrol hissi ve üs kurması, Valheim'ın keşif/hayatta kalma döngüsü.

## Temel kararlar (KARAR — 2026-06-12)

1. **Perspektif: tepeden** (V-Rising benzeri açılı izometrik kamera, ~50°).
2. **Ateşli silah YOK.** Dövüş Knight Online tarzı yakın dövüş; **combo sistemi
   oyunun kalbi** (aşağıda).
3. **Ölüm cezası: eşya düşmez.** Oyuncu kamp ateşinden yeniden doğar
   (kamp ateşi = checkpoint + dinlenme/craft noktası adayı).
4. **Önce tek oyuncu.** Çok oyunculu kesin hedef ama dikey dilimler tek oyuncu
   üstünde ilerler; mimari MP'ye hazır kurulur (deterministik dövüş, durum
   yönetimi server-authoritative düşünülerek yazılır).

## Dört oyundan ne alıyoruz?

| Kaynak | Alınan | Kapsam |
|---|---|---|
| **Knight Online** | Yakın dövüş + combo ustalığı, level/class iskeleti, ileride clan/PvP | ÇEKİRDEK |
| **V-Rising** | Tepeden kamera + WASD/imleç kontrol şeması, üs kurma, craft istasyonları | Çekirdek (kamera dilim 1, üs dilim 3) |
| **Valheim** | Biome keşfi, hafif hayatta kalma (yemek = buff), gece/gündüz tehlike ritmi | Dilim 2 |
| **Remnant 2** | Sert ama adil boss tasarımı, dodge zamanlama hissi (ilham) | Boss tasarım ilkesi |

## Combo sistemi (oyunun kalbi — taslak v1)

KO'daki ustalık hissinin modern hali: kolay öğrenilen, zor ustalaşılan.

- **Zincirler:** Hafif (H) ve Ağır (A) saldırılar dallanan zincirler kurar:
  `H-H-H` hızlı seri, `H-H-A` geniş alan bitirici, `H-A` guard-kırıcı,
  `A-A` yavaş ama devirici.
- **Zamanlama penceresi:** Her vuruşun "perfect" girdi penceresi var; tutturunca
  zincir hızlanır ve vuruş parlar (görsel/ses ödülü).
- **İptal (animation-cancel):** Dodge ve yetenekler belli karelerde saldırıyı
  iptal edebilir — KO'daki skill-cancel ustalık tavanının karşılığı.
- **Combo sayacı:** Kesintisiz vuruş serisi sayaç + hasar çarpanı yükseltir;
  hasar yiyince sıfırlanır.
- **Class çeşitliliği (ileride):** Aynı sistem farklı silah takımlarıyla
  (çift kılıç / iki elli / kalkanlı) farklı zincir setleri sunar.

## Sanat yönü (sahne DNA'sından — koddan geliyor, KESİN)

- Atmosfer: koyu gotik; yoğun mavi-gri sis, neredeyse gece ortamı
- İlk sahne ("Thorny Ivy" haritası): oyuncu başlangıcı → köy kapısı (solda büyük,
  sağda küçük kulübe) → yol kenarında kamp ateşi → çam/köknar ormanı →
  Z=+85'te gotik kale (karanlık taş, ince kuleler, tepede sihirli ışın)
- Render: Unity **HDRP**, linear color space
- Asset üretimi: **Blender ile kendi üretimimiz** (`scripts/blender/` üretim
  hattı, .blend kaynakları oyun reposunda versiyonlu), dokular için HF hattı,
  animasyonlar için Mixamo

## Dikey dilim 1 — "Kamp ateşinden kaleye"

Tek sahnede tam oyun döngüsü (tepeden kamera ile):
1. Oyuncu köy kapısında doğar (Mixamo rigli savaşçı)
2. Ormandan kaleye giden yolda 1 düşman tipi: **Brute** (yakın dövüş)
3. Dövüş: H/A zincirleri (en az 3 zincir) + dodge-roll + stamina + combo sayacı
4. Kamp ateşi: checkpoint + can yenileme; ölünce burada doğar, eşya düşmez
5. Kale kapısında mini-boss → dilim biter
- Başarı ölçütü: 10 dakikalık, combo'su tatmin eden, "bir tur daha" dedirten koşu.
  AAA *kalite hedefi* görsel tutarlılık + dövüş hissiyatında; kapsam şişirme yok.

## Teknik omurga

- Unity (HDRP) + UnityTools AI Autopilot (bu repo) sahne kurulum/iterasyonunda
- Karakter: Mixamo rig + `MixamoAnimationImporter` / `CharacterModelSwapper`
- Düşman: `EnemyAnimatorSetup` + `EnemyMaterialSetup` hattı
- Sahne: `SceneBuilder` (Thorny Ivy v4) — `Assets/FantasyRPG` altında GLB'leri
  isimle arar (PineTree, FirTree, IslandTree, DeadTreeTrunk, TreeStump1/2,
  StoneFire, Boulder1, Rock9, Barrel1, WoodenCrate1, Lantern, CastleDoor,
  IronGate, ModularFort, ...) — üretilen asset adları bu listeyle eşleşmeli
- Asset envanteri ve üretim sırası: `docs/ASSET_REBUILD_PLAN.md`
- **Versiyonlama: oyun projesi 1. günden git'te** (`scripts/init_game_repo.ps1`)
