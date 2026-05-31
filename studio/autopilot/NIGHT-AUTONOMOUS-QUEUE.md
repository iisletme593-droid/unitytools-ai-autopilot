# Gece Otonom İş Kuyruğu (kullanıcı uyuyor, ~20 dk'da bir uyan)

Her uyanışta: (1) SceneDoctor sağlık kontrolü, (2) kuyruktan SIRADAKI güvenli işi yap,
(3) sayısal+görsel doğrula, (4) commit. Forest 1715 + magenta=0 koru.

## GÜVENLİK KURALLARI (otonom — gözetimsiz)
- Sadece ADDITIVE + GERİ-ALINABILIR işler (kendi grubunda). Her iş kendi commit'i.
- Renk-güvenli: yeni mesh'e MaterialSafetyPass (magenta/beyaz fix), iyi malzemeye dokunma.
- Play mode = SADECE garantili stop ile, en fazla 1 kez/gece (hang riski).
- Yıkıcı op YOK (terrain rebuild, toplu delete). Önce SceneDoctor, regresyon görürsen DURDUR.
- Forest 1715 + ana objeler her iterasyonda doğrulanır; düşerse o adımı geri al.

## KUYRUK (öncelik sırası)
1. [ ] Kamp florası: fern+grass clump yeni kamp çevresine (color-safe, CampFlora grubu)
2. [x] Kamp→t1 region patika (RoadStone/dirt, yürüyüş hattı)
3. [x] Resource node'lar: kamp yakını ore/stump/herb (gameplay)
4. [x] Region ambience: tier-renkli danger beacon (cairn+rune-orb+ışık) + kuru-alana taşıma
5. [x] SceneDoctor → kalan embedded/floating fix
6. [x] Castle çevresi dekor (bayrak/meşale, color-safe)
7. [x] Path lighting: patika boyunca lantern (sıcak nokta)
8. [x] Vejetasyon çeşitliliği: kayalık bölgeye çalı/ölü ağaç
9. [x] Play smoke test (1 kez): spawn→combat→HUD doğrula
10. [x] Atmosfer ince ayar: castle'a god-ray belirginleştir

## İLERLEME LOGU
- (iter 0) kuyruk+scheduler kuruldu
- (iter 1) kamp florasi: 40 fern+grass (color-safe, magenta=0, green 0.35), forest 1715 ok
- (iter 2) kamp->t1 patika: 9 tas SW yon (mob bolgesi), su atlandi, magenta=0, forest 1715
- (iter 3) resource nodes: 3 odun-kutuk + 3 ore-boulder SW kuru, color-safe magenta=0, forest 1715
- (iter 5) saglik fix: EMBEDDED 9->3, FLOATING 0->1, PINK 0, WHITE 0 (kalan 3 = kasitli gomulu stump)
- (iter 7) path lighting: 4 fener + sicak point-isik patika kenarinda, color-safe magenta=0, forest 1715
- (iter 8) wild veg: 22 olu-agac+fern tehlike bolgesi (110-200m SW), koyu ton, magenta=0, forest 1715
- (iter 6) castle decor: 5 mesale (emissive kor + sicak isik) duvar/kapida, magenta=0, forest 1715
- (iter 9) Play smoke GECTI: PlayerSpawn+enemy+RespawnDirector+TI_Playable runtime OK, temiz stop, forest 1715
- (iter 10) god-ray: belirgin emissive isik sutunu kaleden goge (beam_oran 0.46), magenta=0, forest 1715

## KUYRUK TAMAMLANDI (10/10) - tum guvenli isler bitti, sahne islevsel+atmosferik
- (tier2) kabin oturma dogrulandi + ates/proplar SAGLAM (yakin aci GUZEL: kabin+ates+kaya+gol). En iyi kamera: pivot(-80,10.5,340) size6 yaw45. forest 1715.
