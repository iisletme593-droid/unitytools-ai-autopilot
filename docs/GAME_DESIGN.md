# THORNY IVY — Oyun Tasarım Dokümanı (v0.1 — TASLAK)

> ⚠️ Bu doküman, kaybolan sohbet geçmişindeki vizyonu yeniden yakalamak için yazıldı.
> Kaynaklar: (1) kullanıcının tarifi — "Remnant 2 + Knight Online + V-Rising + Valheim
> karışımı, AAA kalite", (2) repodaki hayatta kalan sahne DNA'sı (`SceneBuilder.cs v4`).
> `[ONAY?]` etiketli her madde varsayımdır; kullanıcı düzelttikçe güncellenecek.
> **Bu dosya artık oyunun kalıcı hafızasıdır — vizyon değişiklikleri buraya işlenir.**

## Tek cümle

Koyu gotik bir fantezi dünyasında geçen, üçüncü şahıs aksiyon-RPG: Remnant 2'nin
dövüş hissi, Valheim'ın hayatta kalma/keşif döngüsü, V-Rising'in üs kurma sistemi
ve Knight Online'ın PvP/clan ruhu.

## Dört oyundan ne alıyoruz?

| Kaynak | Alınan | Kapsam |
|---|---|---|
| **Remnant 2** | An-be-an dövüş: nişan, dodge-roll, stamina, sert ama adil boss savaşları | Çekirdek (dilim 1) |
| **Valheim** | Biome keşfi, hafif hayatta kalma (yemek = buff), gece/gündüz tehlike ritmi | Çekirdek (dilim 2) |
| **V-Rising** | Üs kurma, craft istasyonları, kaynak toplama → ekipman üretimi | Orta vade (dilim 3) |
| **Knight Online** | Level/class iskeleti, clan yapısı, açık dünya PvP bölgeleri | Uzun vade [ONAY?] |

- Perspektif: **üçüncü şahıs, omuz üstü** (Remnant tarzı) `[ONAY?]`
- Multiplayer: önce **tek oyuncu dikey dilim**; co-op/PvP mimari olarak planlanır ama
  dilim 1'de YOK `[ONAY?]` — (MMO ölçeği tek kişilik ekip için ilk hedef olamaz;
  KO ruhu önce sistem tasarımına, sonra netcode'a girer.)

## Sanat yönü (sahne DNA'sından — bunlar KESİN, koddan geliyor)

- Atmosfer: koyu gotik; yoğun mavi-gri sis, neredeyse gece ortamı
- İlk sahne düzeni ("Thorny Ivy" haritası):
  - Z=0: oyuncu başlangıcı (kamera arkada)
  - Z=+15: köy kapısı — solda büyük kulübe, sağda küçük kulübe
  - Z=+10: yol kenarında kamp ateşi (→ checkpoint/dinlenme noktası adayı)
  - Z=±10–80: yolun iki yanında çam + köknar ormanı
  - Z=+85: gotik kale — karanlık taş, ince kuleler, tepesinde sihirli ışın
- Render: Unity **HDRP**, linear color space
- Asset üretimi: **Blender 5.1 ile kendi üretimimiz** (Asset Store'a bağımlılık yok),
  dokular için HuggingFace üretim hattı (`hf_asset_generator` manifest akışı),
  animasyonlar için Mixamo

## Dikey dilim 1 — "Kamp ateşinden kaleye" (ilk oynanabilir hedef)

Tek sahnede tam bir oyun döngüsü:
1. Oyuncu köy kapısında doğar (Mixamo rigli savaşçı)
2. Ormandan kaleye giden yolda 1 düşman tipi: **Brute** (yakın dövüş)
3. Dövüş: hafif/ağır saldırı + dodge-roll + stamina + kilitlenme (lock-on)
4. Kamp ateşi: checkpoint + can yenileme (ölünce buradan doğar)
5. Kale kapısında mini-boss → dilim biter
- Başarı ölçütü: baştan sona 10 dakikalık, ölümün cezası olan, "bir tur daha" hissi
  veren bir koşu. AAA *kalite hedefi* görsel tutarlılık + dövüş hissiyatında; kapsam değil.

## Teknik omurga

- Unity (HDRP) + UnityTools AI Autopilot (bu repo) sahne kurulum/iterasyonunda
- Karakter: Mixamo rig + `MixamoAnimationImporter` / `CharacterModelSwapper`
- Düşman: `EnemyAnimatorSetup` + `EnemyMaterialSetup` hattı
- Sahne: `SceneBuilder` (Thorny Ivy v4) — asset'ler hazır olunca sahneyi kendisi kurar
- **Versiyonlama: oyun projesi 1. günden git'te** (`scripts/init_game_repo.ps1`);
  .blend kaynakları dahil. Bir daha hiçbir şey kaybolmayacak.

## Açık sorular (kullanıcıya)

1. Perspektif onayı: omuz üstü TPS mi, yoksa V-Rising gibi tepeden mi?
2. Dilim 1 silahlı mı? (Remnant ateşli silah ağırlıklı; KO/Valheim yakın dövüş.
   Taslak varsayım: yakın dövüş + basit yay `[ONAY?]`)
3. Ölüm cezası: Valheim tarzı "eşyalar cesette kalır" mı, sadece checkpoint'e dönüş mü?
4. Multiplayer'ın gerçekçi hedefi: co-op (2-4) mü, KO tarzı sunuculu PvP mi, ikisi de mi?
