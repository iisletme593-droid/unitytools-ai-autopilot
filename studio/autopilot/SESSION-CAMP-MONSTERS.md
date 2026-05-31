# Oturum — Kamp → Canavar → Bölge → Animasyon (öncelik sırası)

Kullanıcı: "kale değil, önce KAMP ALANI; sonra karakterler, canavarlar, bölgeler,
animasyonlar." Hepsi autopilot (bridge + editor MenuItem) ile, commit'li.

## ✅ KAMP ALANI (#1)
- job_build_camp: campfire + 7 taş halkası + 4 kütük oturak + 3 odun + 2 depo
  + 3 sıcak lantern + 8 fern (CampHub).
- job_clearcamp: CampForest (58 beyaz-shard CardFir) SİLİNDİ → kamp açıldı.
  WHITE_SHARD 0.12→0.009, magenta≈0. Işık huzmeleri kaleye taşındı.

## ✅ CANAVARLAR — 15 İŞLEVSEL düşman ⭐
- KEŞİF: bridge Gameplay.* script ekleyemez. DOĞRU YOL: Editor MenuItem +
  execute_menu_item "Assets/Refresh" (derler) + MenuItem çalıştır.
- PopulateMonsterSpawns.cs → 11 marker'a brute mesh + EnemyAIController +
  CombatComponent + CharacterController + Animator(AC_Enemy) + magenta-fix.
- BUG: RequireComponent(CharacterController) → AI'yi İLK eklemek gerekti (yoksa
  PLACED=0). self-log (File.WriteAllText) ile bulundu (Console bridge'den okunamaz).
- DOĞRULAMA: Monsters_cc=15, tam comp stack, GÖRSEL 3D barbarian, Play smoke geçti.

## ✅ BÖLGELER — BOLGE-CANAVAR-TASARIM.md
7 arketip, 6 bölge (Hollow güvenli → tier mesafeyle 4'e çıkar). Mob'lar dağıtıldı.

## ✅ ANİMASYON
3 menü (Import Mixamo / Build Controllers / Setup Enemy Animators) ok=true.
AC_Enemy.controller (Idle/Walk/Run/Attack/Hit/Die/Retreat/Charge) atandı.

## Kritik dersler (belleğe yazıldı)
- Assets/Refresh = C# derleme tetikleyici (refresh_assets YOK)
- Bridge Gameplay.* ekleyemez → Editor MenuItem yaz, self-log koy (Console okunamaz)
- get_object_details bounds flaky; find_scene_objects forest'ı aşınca timeout
- screenshot dönüş `path`'ini oku (timestamp tahmin etme)
