# Briar Hollow — Elle Yerleştirme Kılavuzu (Unity Editörü)

Sahne: **Assets/Scenes/ForgottenValley_VS.unity** (açıkken yap)

Şu an sahnede HAZIR olanlar:
- 🌲 Orman: 953 ağaç (WorldForestGLB) — koyu yeşil, hazır
- 🏕️ Kamp: CampSite (7 prop) + Campfire @ **(-526, 142, -98)**
- 🧍 SK_Hero @ (-526, 138, -102) — olgun gameplay sistemi bağlı (TI_Playable)
- ☀️ Gündüz ışığı (Sun1) + 4 katman PBR zemin

Eksik (domain-reload uçurdu): **EV ve KALE**. Aşağıdaki gibi geri koy.

---

## 1) AHŞAP EV yerleştir

1. Project penceresi → `Assets/70-woodhouse/WoodHouse/WoodHouse.fbx`'i Hierarchy/Scene'e **sürükle**.
2. Inspector → Transform:
   - **Position:** `X -511  Y 144  Z -90`
   - **Rotation:** `X 0  Y 150  Z 0`   (Y'yi kampa bakacak şekilde çevir)
   - **Scale:** `0.75  0.75  0.75`  (gerçek kulübe boyutu ~12m)
3. Malzeme: WoodHouse mesh'ine Inspector'dan
   `Assets/FantasyRPG/Generated/Materials/HDRP_M_WoodHouse.mat`'ı sürükle.
   (Bu malzemede ahşap Diffuse+normal zaten bağlı.)
4. Yere oturmuyorsa Y'yi ±1 oynat (zemin yüzeyi ~144).

---

## 2) KALE yerleştir

1. Project → `Assets/Art/HQ/CastleV2.fbx`'i Scene'e sürükle.
   (Bu, ModularFort kit parçalarından birleştirilmiş kale — 24 parça, kuleler+surlar.)
2. Inspector → Transform:
   - **Position:** `X -516  Y 142  Z -168`   (kampın ~70m kuzeyi, manzarada arkada)
   - **Rotation:** `X 0  Y 0  Z 0`  (FBX dik gelir; yatıksa X'i -90 dene)
   - **Scale:** `2.2  2.2  2.2`  (~150m görkemli kale)
3. Malzeme: `Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat`'ı
   kalenin mesh'ine sürükle (PavingStones taş dokusu + normal, tile 6x6).
4. Taban yere gömülü/havada ise Y'yi ayarla (zemin yüzeyi ~142; kale tabanı yüzeyde olsun).

## 2b) KAHRAMANI KAMPA AL (şu an gölde!)
SK_Hero şu an **(225, 57, 75)** = haritanın öbür ucu, göl kenarı. Kampa taşı:
1. Hierarchy → **SK_Hero** seç.
2. Transform → **Position:** `X -529  Y 143  Z -101` (PlayerSpawn yanı, kamp ateşi başı).
   (Not: oyunu Play'e basınca karakter-seçim sonrası zaten PlayerSpawn'a ışınlanır;
    bu elle taşıma sadece editörde sahneyi düzgün görmen için.)

---

## 3) Işık / Atmosfer (zaten ayarlı, gerekirse)

- Hierarchy'de **UnityTools_HDRPVolume** → Exposure (Fixed) **= 13.8**
  (Daha parlak istersen DÜŞÜR, daha karanlık istersen YÜKSELT — HDRP ters.)
- Güneş: **Sun1**, Intensity 95000, Rotation X48 Y-32.

---

## 4) Kaydet (ÇOK ÖNEMLİ)

Her değişiklikten sonra **Ctrl+S**. Bu projede sahne binary; Play'e basıp
çıkınca veya script derlenince kaydedilmemiş eklemeler kaybolabiliyor.

---

## İpuçları
- Bir objeyi seçip Scene view'da **F** = ona zoom (hızlı bulma).
- Ev/kale ters/yan görünürse Rotation X'i 0 ↔ -90 arası dene (FBX Z-up çevirisi).
- Ağaç eklemek istersen: `Assets/Art/HQ/LP_Fir_GLB.glb` (koyu, blok değil) sürükle,
  malzeme `HDRP_M_CardNeedle.mat`, scale ~6-11.
- KULLANMA: CardFir.glb (yakından siyah blok), Castle.fbx (eski basit kale).
