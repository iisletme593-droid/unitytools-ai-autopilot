# Briar Hollow — Otonom İnşa Durumu (30 May, sabah)

## GÜNCELLEME (30 May 20:35) — ÖNCELİK DEĞİŞTİ: kamp→karakter→canavar→bölge→animasyon
Kullanıcı: "kale değil, önce KAMP ALANI; sonra karakterler, canavarlar, bölgeler,
animasyonlar." Kale görsel grinding'i bırakıldı. Bu sıraya göre yapıldı:

**1. ✅ KAMP ALANI (öncelik #1)** — `job_build_camp.py` + `job_clearcamp.py`:
   - test_campfire.glb merkez ateş (zemine oturtuldu) + 7 taş ateş halkası +
     4 kütük oturak + 3 odun yığını + 2 depo(GothicCabinet) + 3 lantern(sıcak ışık)
     + 8 fern → **CampHub 31 obje**
   - KÖK SORUN bulundu+çözüldü: `CampForest` = kamp üstüne bindirilmiş 58 düşük-
     kalite CardFir (beyaz shard) → SİLİNDİ, kamp açıldı. Stray tmpx probe silindi.
     Işık huzmeleri (kampta kalmıştı) kaleye taşındı. WHITE_SHARD 0.12→0.009.

**2. ✅ CANAVARLAR** — `job_place_monsters.py`: **13 mob** 11 spawn marker'ına:
   - Wanderer×2, Swarm×3, Stalker, Brute, Caster, Archer, **Elite BOSS** (arena)
   - Her biri arketip-tuned `EnemyAIController` + `CombatComponent` (hp tier'a göre,
     factionId=2 hostile). `EnemyRespawnDirector` Start'ta otomatik register eder.
   - DOĞRU bridge komutu: `configure_behaviour_component` (object_name/behaviour_name/
     fields) + `add_behaviour_component`. `set_component` YOK.
   - EnemyAIController animator'u null-guard'lı → animsız da çalışır (move/chase/attack).

**3. ✅ BÖLGELER** — `BOLGE-CANAVAR-TASARIM.md`: 7 arketip, 6 bölge (Hollow güvenli →
   Whispering Pines t1 → Mistfen t2 → Black Marsh t2 → Castle Approach t3 → Boss
   Arena t4). Mob'lar bu tasarıma göre dağıtıldı.

**4. ✅ ANİMASYON KLİPLERİ** — `gen_anims.py`: KEŞİF: hero+enemy aynı 65-bone Mixamo
   rig AMA projede HİÇ klip yok. Prosedurel üretildi → Art/Animations/CharAnims.fbx
   (Idle/Walk/Run/Attack). KALAN: animator controller (Locomotion blend + trigger)
   + Animator assign — vision stabil olunca (blind-wiring riskli).

**Bu turun bridge gerçekleri:** configure_behaviour_component doğru komut;
EnemyArchetype/CombatComponent default'ları sağlam; vision + dosya-display bu turda
çok aralıklı (yeşil vadi + temiz kamp GÖRÜLDÜ, sonra placeholder). Tüm işler
sayısal doğrulandı + commit'lendi. forest 1736 korundu.

---


## GÜNCELLEME (30 May 18:30) — AAA mood/silüet pass + iki kritik altyapı dersi
**Bu turda yapılan (hepsi bridge-uygulandı + kaydedildi + commit'lendi):**
- **Sinematik mood**: parlak öğlen → soğuk overcast dark-fantasy. Slate-mavi
  procedural skybox + bounded cool fog (mfp 440) + alçak sıcak güneş (75k, x16
  açı) + EV 12.0 (süpürmeyle seçildi). Sayısal: hero parl=95, soğuk=0.55,
  gök_doygunluk düşük. (job_mood.py, job_mood2.py, job_mood_lock.py)
- **Ocak sıcak havuz** (art_bible #1 aksan): CampfireLight + HearthEmber emissive
  + WindowGlow. sıcak_oran=0.020 (tek-aksan). (job_hearth.py)
- **Kale gotik silüet**: 5 sivri kule (4 köşe + donjon), oran 0.70→**1.68**.
  (job_spires.py)
- **Kale gömülmesi TEKRAR çıktı + düzeltildi**: taban 124.8 vs gerçek zemin 142.6
  (uzak probe ile kesin), +17.2m kaldırıldı → taban 142.0. (job_lift_castle.py)

**KRİTİK: ekran görüntüsü yolu** — capture dönüşündeki `path` alanı
`studio/qa/screenshots/`'a kopyayı, `source` alanı AutopilotData'daki orijinali
verir. TÜM seans `source`'un timestamp'ini TAHMİN edip yanlış dosya okuyordum →
sahneyi hiç görememiştim. Doğru yol = capture'ın döndürdüğü `path`.

**KRİTİK: enstrümantasyon kırılgan** — uzun seansta hem görüntü teslimi
("[Image content not available]", sentetik PNG dahi) hem çok-satırlı stdout/JSON
okuma bozulabiliyor. Çözüm: tek-değer sayısal doğrulama (grep -oE "ETIKET=deger").
Bridge edit'leri + save etkilenmiyor.

**7 referans öğesi DURUM (sayısal mevcut, GÖRSEL onay render dönünce):**
kamp ateşi+çim ön plan ✓ · kabin ✓ · çam ormanı (1848) ✓ · uzakta gotik kale
(silüet 1.68, oturmuş) ✓ · ilahi ışık huzmesi (emissive) ✓ · sis ✓ · soğuk mood ✓
Kalan: GÖRSEL kalite/kompozisyon yargısı (kule zarafeti, malzeme realizmi).

---


## EN ÖNEMLİ DÖNÜM: olgun sistem entegre edildi
Kullanıcı kararı: **"mevcut sistemi kullan, benimkileri kaldır."**

Keşif: Projede ZATEN dökümana-hizalı OLGUN bir gameplay sistemi varmış
(`Assets/Scripts/Gameplay/`): PlayerController (444 sat, dodge/coyote/lock-on/
stamina/combat), EnemyAIController (617), RpgHudController (466), MinimapController,
ThirdPersonCamera, + bir sürü Gameplay.* bileşeni — `Main.unity`'de kuruluymuş.
Gece yazdığım 12 basit IMGUI scripti bunun ilkel paralel kopyasıydı.

Yapılan:
1. **Gece 12 IMGUI scriptini diskten sildim** (çakışma yok, derleme temiz).
2. **SK_Hero gerçek modelini** kampa yerleştirdim (PlayerSpawn -529,141,-101).
3. **`wire_playable_slice`** ile olgun sistemi `ForgottenValley_VS`'e kurdum:
   ok=True, **39 bileşen, missing=[]**.
   - SK_Hero = 12 comp (CharacterController/Stamina/Inventory/Experience/Combat/
     StatusEffect/PlayerController/StatusInfliction/PlayerLevelPassives/PotionSystem)
   - TI_HUD = 14 comp (RpgHud/HudShells/HudAutoBuilder/PauseMenu/DayCycleHud/
     CompassHud/CharacterStatsPanel/BossHealthBarHud/FlaskHud)
   - + TI_Minimap/Weather/NightDanger/SkyboxManager/DayCycleManager/MusicDirector/
     AudioManager/MainMenuOverlay/RegionStreamer/TutorialDirector/RunStats/GameSettings

## DOĞRULANDI (kanıtlı)
- `check_compile`: **OK 0 errors**.
- Play testi: **is_playing=True, SK_Hero runtime=OK, TI_HUD runtime=OK**, temiz çıkış.
- Tek runtime istisna: Unity AI Toolkit hesap servisinden 2 NRE (oyun kodu DEĞİL).
- Forest 1848 + tüm çevre (kamp/kale/arena/yol/kaynaklar) sağlam.

## Sahne = ForgottenValley_VS (tek doğru sahne)
- OpenMainSceneOnStartup.cs düzeltildi → artık bunu açıyor (Main.unity değil).
- SK_Hero kampta, "Player" tag'li, olgun controller + HUD bağlı.
- Çevre: orman 1848, CampSite/Dressing/Warmth, RoadDressing, Ferns, RockScatter,
  ResourceNodes 16, RestPoint, BossArena, EncounterMarkers, RumorBoard, CraftStation,
  grander gotik kale + huzme, karanlık-fantezi atmosfer.

## Doğrulama yöntemi (oturdu)
- `.cs` → `_clean_verdict.py` (refresh) → `check_compile.py` ("OK 0 errors" şart).
- Runtime → `_playverify.py` (Play 7 sn, is_playing + obje kontrolü).
- Editor.log "error CS" + Exception taraması (AI Toolkit NRE'leri yok say).

## Sıradaki (olgun sistem üstüne, doğrulanabilir)
- Düşmanları sahneye bağla: MonsterSpawns/EncounterMarkers'a Gameplay.EnemyAI +
  gerçek enemy modeli (Monster_UE/Stalker_22/brute) — wire'da enemy kurulumu
  var mı kontrol et (1347+ satırda enemy/totem authoring olabilir).
- Build ayarlarına ForgottenValley_VS'i sahne-0 yap (oyun bununla açılsın).
- audio-campfire hâlâ BLOKLU (ses dosyası yok) ama AudioManager prosedürel
  müzik/SFX üretiyormuş — gerçek dosya gerekmeyebilir, kontrol et.

## Not
Unity projesi git'siz/ayrı; C# kodu diskte canlı. Commit'ler studio/autopilot +
docs için. Gece IMGUI scriptleri tamamen kaldırıldı (geri dönülmedi).

## GORSEL KALITE TURU (30 May ogle) — kullanici geri bildirimi
Kullanici: "agaclar guzel ama kale/ev/zemin referansa benzemiyor, gercekci degil."
Uc sorun da gercek PBR ile cozuldu:
1. ZEMIN: duz tek-renk yesil -> apply_terrain_pbr_layers + AmbientCG 2K setleri
   (Ground054 cim / Ground104 yosunlu orman / Ground103 toprak / Ground037 cakil,
   Color+NormalGL, yukseklik bandi). Fotogrametri dokulu zemin.
2. EV: prosedurel duz-shade kutu -> gercek 70-woodhouse/WoodHouse.fbx +
   HDRP_M_WoodHouse (Diffuse+normal atlasi). Ahsap plank+kiremit+tas, kamp yani.
3. KALE: duz gri -> HDRP_M_CastleStone (PavingStones150 tas dokusu, tile 8x8,
   Color+NormalGL). ModularFort.glb denendi ama 'moduler kit' (dagimik) cikti,
   kullanilmadi; prosedurel kalenin silueti + gercek tas doku tutuldu.
Sonuc: overview kareleri -> zemin+agac+ev+kale uyumlu, gercekci orman vadisi.
Kalan ince ayar (istege bagli): kale cati kiremit dokusu, pencere isiklari,
ev/kale/kamp konum kompozisyonu (su an biraz dagimik: ev -517, kale -482/-311,
kamp -533).

## KRITIK DERS (30 May): PLAY MODU YANILGISI
Oturum boyunca "orman gitti (1848->1)" defalarca paniğe yol açtı. GERCEK SEBEP:
sorgular PLAY MODUNDAYKEN yapilinca Unity'nin RUNTIME (gecici) sahne kopyasini
okuyor, gercek editor sahnesini DEGIL. Play'den cikinca forest=1848 GERI GELDI
-> hicbir sey kaybolmamis. Ayrica rebuild_scene Play'de calisinca ev/kale
"cannot be used during play mode" ile FAIL veriyordu.
KURAL: her bridge sorgusu/duzenlemesi ONCESI get_editor_state ile is_playing
kontrol et; True ise play_mode False yap. ap.py guard'a eklenebilir.

## KARE PIPELINE (B+A tamam)
- shot_triage.py v2: binlerce kareyi sayisal+dHash ele -> cesitli ~22 kritik kare
- aaa_score.py: sinematik 0-100 skor (kompozisyon/ufuk/derinlik/renk/kontrast/...)
- capture_orbit.py + review_loop.py: cok-aci otomatik snapshot + ele
- rebuild_scene.py: tek komut tum sahne + her adim save (Play KAPALI olmali)
Akis: (Play kapat) -> rebuild gerekiyorsa -> capture -> triage+aaa -> ben en
iyi/en kotu ~20 kareyi oku -> duzelt -> tekrar.

## GUNCEL GERCEK DURUM (Play kapali, dogrulanmis)
forest 1848 + WoodHouse(-510,135,-88) + GothicCastle(-482,94,-311, UZAK 217m) +
Campfire + CampSite + CampForest(70) + SK_Hero kampta. Agaclar KOYU YESIL (artik
beyaz degil). Kalan: bazi CardFir yakindan siyah-blok; kale kamptan uzak
(kompozisyon); zemin yer yer cipak.
