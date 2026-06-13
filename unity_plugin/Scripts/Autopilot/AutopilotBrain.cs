#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace Autopilot
{
    // ─────────────────────────────────────────────────────────────────────────
    //  THORNY IVY — SMART AUTOPILOT BRAIN
    //  Sahneyi analiz eder, nelerin eksik/bozuk oldugunu tespit eder ve
    //  onceliklere gore otomatik olarak duzeltir.
    //  Acilis: Tools > Autopilot > ★ Smart Autopilot Brain
    // ─────────────────────────────────────────────────────────────────────────

    // ── Ogrenme kayitlari ─────────────────────────────────────────────────────
    [Serializable] class FixRecord  { public string fixId; public float scoreBefore; public float scoreAfter; public string timestamp; }
    [Serializable] class LearningData
    {
        public int            totalCycles;
        public float          peakScore;
        public List<FixRecord> history       = new List<FixRecord>();
        public List<string>   exhaustedFixes = new List<string>();
    }

    // ── Otomatik döngü yöneticisi ─────────────────────────────────────────────
    // Unity başladığında veya domain reload sonrası otomatik devreye girer.
    [InitializeOnLoad]
    internal static class AutopilotBrainLoop
    {
        const string KeyEnabled   = "ThornyIvy_BrainLoop_Enabled";
        const string KeyNextRun   = "ThornyIvy_BrainLoop_NextRun";
        const string KeyInterval  = "ThornyIvy_BrainLoop_Interval"; // dakika
        const string KeyAutoStart = "ThornyIvy_BrainLoop_AutoStarted";

        internal static bool   IsEnabled => SessionState.GetBool (KeyEnabled,  false);
        internal static float  Interval  => SessionState.GetFloat(KeyInterval, 10f);
        internal static double NextRun   => (double)SessionState.GetFloat(KeyNextRun, 0f);

        static AutopilotBrainLoop()
        {
            if (!AutopilotExecutionMode.ShouldRunAutomatic("BrainLoop"))
            {
                SessionState.SetBool(KeyEnabled, false);
                return;
            }
            EditorApplication.update += Tick;
            // İlk açılışta otomatik başlat (session başına bir kez)
            if (!SessionState.GetBool(KeyAutoStart, false))
            {
                SessionState.SetBool(KeyAutoStart, true);
                SessionState.SetBool(KeyEnabled, false);
            }
        }

        internal static void SetEnabled(bool on, float intervalMinutes = 10f)
        {
            if (on && !AutopilotExecutionMode.AllowAutomaticLoops)
            {
                SessionState.SetBool(KeyEnabled, false);
                Debug.Log("[BrainLoop] Otomatik dongu kapali. Chat/menu komutlari manuel calisir. Etkinlestirmek icin Tools > Autopilot > Mode > Enable Automatic Loops.");
                return;
            }
            SessionState.SetBool (KeyEnabled,  on);
            SessionState.SetFloat(KeyInterval, intervalMinutes);
            if (on)
                SessionState.SetFloat(KeyNextRun, (float)(EditorApplication.timeSinceStartup + intervalMinutes * 60.0));
            Debug.Log($"[BrainLoop] Otomatik döngü {(on ? "AÇILDI" : "KAPATILDI")}" +
                      (on ? $" — her {intervalMinutes:F0} dakikada bir çalışacak." : "."));
        }

        static void Tick()
        {
            if (!IsEnabled) return;
            if (EditorApplication.isPlaying) return;           // play mode'da çalıştırma
            if (EditorApplication.isCompiling) return;         // derleme sırasında çalıştırma
            if (EditorApplication.timeSinceStartup < NextRun) return;

            // Zamanlayıcıyı hemen güncelle (çift tetiklenmeyi önle)
            SessionState.SetFloat(KeyNextRun, (float)(EditorApplication.timeSinceStartup + Interval * 60.0));

            Debug.Log($"[BrainLoop] Otomatik döngü başlıyor... ({DateTime.Now:HH:mm:ss})");
            try
            {
                if (EditorWindow.HasOpenInstances<AutopilotBrain>())
                {
                    // Pencere zaten açık — var olan instance üzerinde çalış
                    var w = EditorWindow.GetWindow<AutopilotBrain>(false, "★ Autopilot Brain", false);
                    if (w != null) { w.AutoRun(); return; }
                }
                // Headless: pencere açmadan direkt logic çalıştır
                AutopilotBrain.RunHeadless();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[BrainLoop] Hata: {ex.Message}");
            }
        }

        internal static string CountdownText()
        {
            if (!IsEnabled) return "Kapalı";
            double remaining = NextRun - EditorApplication.timeSinceStartup;
            if (remaining <= 0) return "Şimdi çalışıyor...";
            int m = (int)(remaining / 60); int s = (int)(remaining % 60);
            return $"{m:D2}:{s:D2} sonra";
        }
    }

    public class AutopilotBrain : EditorWindow
    {
        // ── Istatistik snapshot ──────────────────────────────────────────────
        struct Snap
        {
            public int   glbTotal;          // Assets/FantasyRPG'deki toplam model
            public bool  gltfastActive;     // glTFast ModelImporter'la import edilen mi?
            public bool  rpgSceneExists;    // _RPG_Scene veya _RPG_Forest var mi?
            public int   treeCount;
            public int   rockCount;
            public int   enemyCount;
            public int[] tiersFound;        // mevcut tier numaralari
            public bool  hasPlayer;
            public bool  hasCamera;
            public bool  hasHud;
            public int   rendererCount;
            public int   paintedCount;      // _RPG_Mat_ ile baslayan materyaller
            public bool  heroSwapped;       // SK_Hero_Visual mevcut
            public int   lightCount;
            public bool  fogOn;
            public bool  sceneDirty;
            public string scenePath;
            // Yeni: temizlik durum bilgileri
            public int   strayPrimitives;      // isimsiz/default-isimli root primitifler
            public bool  cameraClean;          // kamera _RPG_ hiyerarsisi disinda mi?
            public bool  dungeonUnderground;   // dungeon Y<-5 mi? (kaleyle cakismiyor mu?)
            public int   islandTreeCount;      // sahnedeki IslandTree nesnesi sayisi
            public int   islandTreePainted;    // arborikultür boyasi uygulanan IslandTree sayisi
            public float visionScore;          // referans görsellerle görsel eşleşme skoru (0-100)
        }

        // ── Kalite kontrol maddesi ────────────────────────────────────────────
        struct Check
        {
            public string label;
            public string detail;
            public int    score;
            public int    max;
            public string fixId;   // hangi fix'i tetikler
            public bool OK      => score >= max;
            public bool Partial => score > 0 && score < max;
        }

        // ── Fix tanimi ────────────────────────────────────────────────────────
        struct Fix
        {
            public string id;
            public string name;
            public string description;
            public Func<bool> run;
        }

        // ── State ─────────────────────────────────────────────────────────────
        Snap           snap;
        List<Check>    checks    = new List<Check>();
        List<Fix>      fixPlan   = new List<Fix>();
        List<string>   log       = new List<string>();
        Vector2        logScroll;
        float          score;
        const float    MaxScore  = 100f;
        bool           autoMode;
        GUIStyle       _h1, _h2, _mono, _icon;
        float          _intervalMin = 10f;  // UI slider değeri
        LearningData   learning;            // öğrenme verileri

        // ── Renkler (dark fantasy palette) ───────────────────────────────────
        static readonly Color CRed    = new Color(0.80f, 0.18f, 0.10f);
        static readonly Color COrange = new Color(0.88f, 0.55f, 0.10f);
        static readonly Color CGreen  = new Color(0.15f, 0.75f, 0.28f);
        static readonly Color CGold   = new Color(0.90f, 0.75f, 0.18f);
        static readonly Color CBlue   = new Color(0.22f, 0.58f, 0.92f);
        static readonly Color CDark   = new Color(0.10f, 0.10f, 0.12f);
        static readonly Color CPurple = new Color(0.55f, 0.20f, 0.90f);

        // ─────────────────────────────────────────────────────────────────────
        [MenuItem("Tools/Autopilot/★ Smart Autopilot Brain", priority = 0)]
        public static void Open() =>
            GetWindow<AutopilotBrain>(false, "★ Autopilot Brain", true);

        void OnEnable()
        {
            minSize      = new Vector2(440, 680);
            _intervalMin = AutopilotBrainLoop.Interval;
            Analyze();
            // Pencere açıkken her 5 saniyede geri sayımı güncelle
            EditorApplication.update += OnEditorUpdate;
        }

        void OnDisable() => EditorApplication.update -= OnEditorUpdate;

        double _lastRepaintTime;
        void OnEditorUpdate()
        {
            if (AutopilotBrainLoop.IsEnabled &&
                EditorApplication.timeSinceStartup - _lastRepaintTime > 5.0)
            {
                _lastRepaintTime = EditorApplication.timeSinceStartup;
                Repaint();
            }
        }

        // Döngü tarafından kod üzerinden çağrılır (pencere açık olmak zorunda değil)
        internal void AutoRun()
        {
            Analyze();
            if (score < MaxScore && fixPlan.Count > 0)
            {
                Log($"[AUTO] Döngü: skor={score:F0}/100, {fixPlan.Count} fix kuyruğu");
                RunAllFixes();
            }
            else
            {
                Log($"[AUTO] Döngü: skor={score:F0}/100 — düzeltme gerekmedi.");
            }
        }

        // Pencere açık değilken döngüden headless çağrılır
        internal static void RunHeadless()
        {
            var tmp = ScriptableObject.CreateInstance<AutopilotBrain>();
            try   { tmp.AutoRun(); }
            finally { ScriptableObject.DestroyImmediate(tmp); }
        }

        // ── Sahne Analizi ─────────────────────────────────────────────────────
        void Analyze()
        {
            snap = default;
            checks.Clear();
            fixPlan.Clear();
            learning = LoadLearning();

            try { DoAnalyze(); }
            catch (Exception ex) { Log($"[HATA] Analiz: {ex.Message}"); }

            BuildChecks();
            BuildFixPlan();
            score = checks.Sum(c => c.score);
            Repaint();
        }

        void DoAnalyze()
        {
            // ── GLB sayimi ───────────────────────────────────────────────────
            snap.glbTotal = AssetDatabase.FindAssets("t:GameObject",
                new[] { "Assets/FantasyRPG" }).Length;

            // glTFast kontrolu: ilk 30 GLB'nin importer'ina bak
            int miCount = 0;
            foreach (var g in AssetDatabase.FindAssets("", new[] { "Assets/FantasyRPG" }).Take(30))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (Path.GetExtension(p).ToLower() == ".glb" &&
                    AssetImporter.GetAtPath(p) is ModelImporter)
                    miCount++;
            }
            snap.gltfastActive = miCount > 5;

            // ── Sahne objeleri ───────────────────────────────────────────────
            snap.rpgSceneExists = GameObject.Find("_RPG_Scene") != null
                               || GameObject.Find("_RPG_Forest") != null
                               || GameObject.Find("_RPG_Castle") != null;

            var forestRoot = GameObject.Find("_RPG_Forest");
            snap.treeCount  = forestRoot  != null ? forestRoot.transform.childCount  : 0;
            var rocksRoot   = GameObject.Find("_RPG_Rocks");
            snap.rockCount  = rocksRoot   != null ? rocksRoot.transform.childCount   : 0;

            // ── Dusman / tier analizi ────────────────────────────────────────
            var enemies = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                FindObjectsInactive.Include);
            snap.enemyCount = enemies.Length;
            snap.tiersFound = enemies.Select(e => e.enemyTier).Distinct().OrderBy(x => x).ToArray();

            // ── Oyuncu / kamera / HUD ────────────────────────────────────────
            snap.hasPlayer = GameObject.FindGameObjectWithTag("Player") != null;
            snap.hasCamera = Camera.main != null;
            snap.hasHud    = UnityEngine.Object.FindAnyObjectByType<Gameplay.RpgHudController>() != null;

            // ── Materyal durumu ──────────────────────────────────────────────
            var renderers = UnityEngine.Object.FindObjectsByType<MeshRenderer>(
                FindObjectsInactive.Include);
            snap.rendererCount = renderers.Length;
            snap.paintedCount  = renderers.Count(r =>
                r.sharedMaterial != null &&
                r.sharedMaterial.name.StartsWith("_RPG_Mat_"));

            // ── Karakter modeli ──────────────────────────────────────────────
            snap.heroSwapped = GameObject.Find("SK_Hero_Visual") != null
                            || GameObject.Find("SK_Model_Visual") != null;

            // ── Isik + sis ───────────────────────────────────────────────────
            snap.lightCount = UnityEngine.Object.FindObjectsByType<Light>(
                FindObjectsInactive.Include).Length;
            snap.fogOn = RenderSettings.fog;

            // ── Sahne meta ───────────────────────────────────────────────────
            var active   = EditorSceneManager.GetActiveScene();
            snap.sceneDirty = active.isDirty;
            snap.scenePath  = active.path;

            // ── Temizlik analizi ─────────────────────────────────────────────
            // Eski autopilot cikintisi: "Cube", "Cylinder" gibi default isimli root primitifler
            string[] strayNames = { "Cube", "Cylinder", "Plane", "Sphere", "Capsule", "Quad" };
            snap.strayPrimitives = UnityEngine.Object.FindObjectsByType<GameObject>(
                    FindObjectsInactive.Include)
                .Count(go => go.transform.parent == null &&
                             (strayNames.Contains(go.name) || go.name.StartsWith("GameObject")));

            // Kamera _RPG_ hiyerarsisinin disinda mi?
            snap.cameraClean = Camera.main == null ||
                               Camera.main.transform.parent == null ||
                               !Camera.main.transform.root.name.StartsWith("_RPG_");

            // Dungeon Y < -5 mi? (kaleyle cakismiyor mu?)
            var dungeonGo = GameObject.Find("_RPG_Dungeon");
            snap.dungeonUnderground = dungeonGo == null || dungeonGo.transform.position.y < -5f;

            // IslandTree arborikültür boyama durumu
            var allGo = UnityEngine.Object.FindObjectsByType<GameObject>(
                FindObjectsInactive.Include);
            foreach (var go in allGo)
            {
                if (go == null || !go.name.Contains("IslandTree", StringComparison.OrdinalIgnoreCase)) continue;
                snap.islandTreeCount++;
                var mrs = go.GetComponentsInChildren<MeshRenderer>(includeInactive: true);
                bool painted = mrs.Length > 0 && System.Array.Exists(mrs, mr =>
                    mr != null && mr.sharedMaterials.Length > 0 &&
                    mr.sharedMaterials[0] != null &&
                    mr.sharedMaterials[0].name.StartsWith("_RPG_IT_"));
                if (painted) snap.islandTreePainted++;
            }

            // Görsel eşleşme skoru (Vision Learner)
            snap.visionScore = AutopilotVisionLearner.GetCurrentScore();
        }

        // ── Kalite kontrolleri olustur ────────────────────────────────────────
        void BuildChecks()
        {
            checks.Clear();

            // 1. GLB Asset havuzu
            int g = snap.glbTotal >= 250 ? 10 : snap.glbTotal >= 100 ? 7 :
                    snap.glbTotal >= 10  ? 3  : 0;
            Add("GLB Asset Havuzu", $"{snap.glbTotal} model", g, 10, "import_glb");

            // 2. glTFast aktif mi?
            int gf = snap.gltfastActive ? 8 : 0;
            Add("glTFast Importer", snap.gltfastActive ? "Aktif — 3D import dogru" : "! GLB'ler binary blob olarak gorünüyor", gf, 8, "fix_gltfast");

            // 3. RPG sahne yapisi
            int rs = snap.rpgSceneExists ? 7 : 0;
            Add("RPG Sahne Yapisi", snap.rpgSceneExists ? "_RPG_ hiyerarsisi mevcut" : "BuildScene henuz calistirilmadi", rs, 7, "build_scene");

            // 4. Orman yogunlugu
            int tf = snap.treeCount >= 80 ? 10 : snap.treeCount >= 40 ? 7 :
                     snap.treeCount >= 10 ? 3  : 0;
            Add("Orman Yogunlugu", $"{snap.treeCount} agac sahada", tf, 10, "build_scene");

            // 5. Kaya formasyonlari
            int rf = snap.rockCount >= 20 ? 7 : snap.rockCount >= 8 ? 4 :
                     snap.rockCount >= 2  ? 2 : 0;
            Add("Kaya Formasyonlari", $"{snap.rockCount} kaya / kayalik", rf, 7, "build_scene");

            // 6. Oyuncu spawni (fix_player ile duzeltilir)
            Add("Oyuncu Spawni", snap.hasPlayer ? "Player tag bulundu" : "Player yok — kritik!", snap.hasPlayer ? 8 : 0, 8, "fix_player");

            // 7. Kamera (fix_camera ile duzeltilir)
            Add("3P Kamera", snap.hasCamera ? "Camera.main aktif" : "Kamera bulunamadi", snap.hasCamera ? 5 : 0, 5, "fix_camera");

            // 8. Dusman sayisi
            int ec = snap.enemyCount >= 16 ? 8 : snap.enemyCount >= 8 ? 5 :
                     snap.enemyCount >= 2  ? 2 : 0;
            Add("Dusman Sayisi", $"{snap.enemyCount} enemy sahada", ec, 8, "build_scene");

            // 9. Tier dagilimi (1-4 hepsi var mi?)
            int tc = snap.tiersFound.Length >= 4 ? 8 : snap.tiersFound.Length * 2;
            string tierStr = snap.tiersFound.Length > 0
                ? "Tier " + string.Join(",", snap.tiersFound) : "Hic tier yok";
            Add("Tier Dagilimi (1-4)", tierStr, tc, 8, "build_scene");

            // 10. Materyal boyama
            float pr = snap.rendererCount > 0 ? (float)snap.paintedCount / snap.rendererCount : 0;
            int ms = pr >= 0.6f ? 10 : pr >= 0.3f ? 6 : pr >= 0.05f ? 2 : 0;
            Add("Materyal Boyama", $"%{pr*100:F0} boyali ({snap.paintedCount}/{snap.rendererCount})", ms, 10, "paint");

            // 11. Karakter modeli
            Add("Karakter Modeli", snap.heroSwapped ? "Gercek FBX aktif" : "Placeholder kullaniliyor", snap.heroSwapped ? 7 : 0, 7, "swap_chars");

            // 12. Isiklandirma + sis
            int ls = (snap.lightCount >= 8 && snap.fogOn) ? 8 : (snap.lightCount >= 4) ? 5 :
                     snap.lightCount > 0 ? 2 : 0;
            Add("Isik + Sis", $"{snap.lightCount} isik, sis={snap.fogOn}", ls, 8, "boost_light");

            // 13. Sahne kaydedildi
            Add("Sahne Kaydedildi", !snap.sceneDirty ? "Kaydedildi" : "Kaydedilmemis degisiklikler var",
                snap.sceneDirty ? 2 : 4, 4, "save");

            // 14. Sahne temizligi (stray primitif / kamera hiyerarsisi / dungeon konumu)
            bool sceneClean = snap.strayPrimitives == 0 && snap.cameraClean && snap.dungeonUnderground;
            string cleanDetail = sceneClean ? "Temiz — cakisma yok"
                : $"Sorun: {snap.strayPrimitives} stray prim" +
                  (!snap.cameraClean ? " + kamera _RPG_ icinde" : "") +
                  (!snap.dungeonUnderground ? " + dungeon kaledeki konumda" : "");
            Add("Sahne Duzen Temizligi", cleanDetail, sceneClean ? 6 : 0, 6, "nuke_rebuild");

            // 15. IslandTree arborikültür boyama
            if (snap.islandTreeCount > 0)
            {
                bool treePainted = snap.islandTreePainted >= snap.islandTreeCount;
                string treeDetail = treePainted
                    ? $"Boyali — {snap.islandTreePainted}/{snap.islandTreeCount} agac"
                    : $"Boyanmamis — {snap.islandTreeCount - snap.islandTreePainted}/{snap.islandTreeCount} agac bekleniyor";
                Add("IslandTree Materyal Boyama", treeDetail, treePainted ? 4 : 0, 4, "paint_island_trees");
            }

            // 16. Görsel eşleşme (Vision Learner — referans görsellere ne kadar yakın?)
            if (snap.visionScore >= 0f)
            {
                int vScore  = Mathf.RoundToInt(snap.visionScore / 100f * 10f);
                string vDetail = snap.visionScore >= 78f
                    ? $"Referans eşleşiyor — {snap.visionScore:F1}/100"
                    : $"Referanstan uzak — {snap.visionScore:F1}/100 (hedef ≥78)";
                Add("Referans Görsel Eşleşmesi", vDetail, Mathf.Clamp(vScore, 0, 10), 10, "vision_learn");
            }
        }

        void Add(string label, string detail, int sc, int max, string fixId) =>
            checks.Add(new Check { label = label, detail = detail, score = sc, max = max, fixId = fixId });

        // ── Fix plani: hangi duzeltme oncelikli? ────────────────────────────
        void BuildFixPlan()
        {
            fixPlan.Clear();

            // Her check'in eksik puanini hesapla, eksige gore sirala
            var needed = checks.Where(c => !c.OK)
                               .OrderByDescending(c => c.max - c.score)
                               .ToList();

            var addedIds = new HashSet<string>();
            foreach (var c in needed)
            {
                if (string.IsNullOrEmpty(c.fixId) || addedIds.Contains(c.fixId)) continue;
                // Tukenmus fix'leri atla
                if (learning != null && learning.exhaustedFixes != null &&
                    learning.exhaustedFixes.Contains(c.fixId)) continue;
                addedIds.Add(c.fixId);

                switch (c.fixId)
                {
                    case "import_glb":
                        fixPlan.Add(new Fix { id = "import_glb", name = "GLB Assetleri Import Et",
                            description = "Fantasy_RPG_Class_Item_Pack'ten Unity'ye kopyalar",
                            run = () => { SceneBuilder.ImportAssets(); return true; } });
                        break;

                    case "fix_gltfast":
                        fixPlan.Add(new Fix { id = "fix_gltfast", name = "glTFast Kontrolu",
                            description = "manifest.json'da com.unity.cloud.gltfast var mi kontrol eder",
                            run = FixGltfast });
                        break;

                    case "build_scene":
                        fixPlan.Add(new Fix { id = "build_scene", name = "Sahneyi Kur / Yenile",
                            description = "SceneBuilder.BuildScene() — orman, kayalik, kale, dusman",
                            run = () => { SceneBuilder.BuildScene(); return true; } });
                        break;

                    case "fix_camera":
                        fixPlan.Add(new Fix { id = "fix_camera", name = "Kamera Ekle",
                            description = "Camera.main + AudioListener yerleştirir",
                            run = () => { SceneBuilder.EnsureCameraAndPlayer(); return Camera.main != null; } });
                        break;

                    case "fix_player":
                        fixPlan.Add(new Fix { id = "fix_player", name = "Player Ekle",
                            description = "Player tag'li Capsule + CharacterController",
                            run = () => { SceneBuilder.EnsureCameraAndPlayer(); return GameObject.FindGameObjectWithTag("Player") != null; } });
                        break;

                    case "paint":
                        fixPlan.Add(new Fix { id = "paint", name = "Materyalleri Boya",
                            description = "Dark fantasy paleti — yaprak/kabuk/tas/metal/emissive",
                            run = () => { SceneMaterialPainter.PaintAll(); return true; } });
                        break;

                    case "swap_chars":
                        fixPlan.Add(new Fix { id = "swap_chars", name = "Karakterleri Degistir",
                            description = "Placeholder → gercek FBX (auto weapon sizing)",
                            run = () => { CharacterModelSwapper.SwapAll(); return true; } });
                        break;

                    case "boost_light":
                        fixPlan.Add(new Fix { id = "boost_light", name = "Isiklandirmayi Guclendir",
                            description = "Fog density, ambient, ek nokta isiklari",
                            run = BoostLighting });
                        break;

                    case "save":
                        fixPlan.Add(new Fix { id = "save", name = "Sahneyi Kaydet",
                            description = "EditorSceneManager.SaveScene",
                            run = () => { EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene()); return true; } });
                        break;

                    case "nuke_rebuild":
                        fixPlan.Add(new Fix { id = "nuke_rebuild", name = "Sahneyi Temizle + Yeniden Kur",
                            description = "Stray primitifleri sil, dungeon'i yeraltina tasi, kamera hiyerarsisini duzelt",
                            run = () => { ClearAndRebuild(); return true; } });
                        break;

                    case "paint_island_trees":
                        fixPlan.Add(new Fix { id = "paint_island_trees", name = "IslandTree Arborikültür Boyama",
                            description = "Broadleaf deciduous palet: kanopi yeşili + kabuk kahvesi, double-sided foliage, subsurface translucency",
                            run = () => IslandTreePainter.RunAsTask(out _) });
                        break;

                    case "vision_learn":
                        fixPlan.Add(new Fix { id = "vision_learn", name = "Vision Learner — Referans Görsel Öğrenmesi",
                            description = "Referans görselleri analiz eder, screenshot karşılaştırır, sis/ışık/renk/ölçek parametrelerini iteratif optimize eder",
                            run = () => AutopilotVisionLearner.RunAsTask(out _) });
                        break;
                }
            }
        }

        // ── Tek adim calistir ─────────────────────────────────────────────────
        void RunNextFix()
        {
            if (fixPlan.Count == 0) { Log("✓ Tum duzeltmeler tamamlandi!"); Analyze(); return; }
            var fix = fixPlan[0];
            ExecFix(fix);
        }

        // ── Tum duzeltmeleri calistir ─────────────────────────────────────────
        void RunAllFixes()
        {
            Log("━━━ TAM OTOMATİK DÜZENLEME BAŞLADI ━━━");
            learning = LoadLearning();
            learning.totalCycles++;
            float prevScore = -99f;
            int stagnant = 0;
            int pass = 0;
            while (pass < 15)
            {
                Analyze();
                if (fixPlan.Count == 0 || score >= MaxScore) break;
                if (score - prevScore < 1.0f) stagnant++;
                else stagnant = 0;
                if (stagnant >= 3) { Log("⚠ Skor artmıyor, döngü durduruluyor."); break; }
                prevScore = score;
                var fix = fixPlan[0];
                float before = score;
                ExecFix(fix);
                Analyze();
                RecordFix(fix.id, before, score);
                pass++;
            }
            if (score > learning.peakScore) learning.peakScore = score;
            SaveLearning(learning);
            Log($"━━━ TAMAMLANDI  Skor:{score:F0}/100  Zirve:{learning.peakScore:F0}  Döngü:{learning.totalCycles} ━━━");
        }

        void ExecFix(Fix fix)
        {
            Log($"â–¶ {fix.name}...");
            try
            {
                bool ok = fix.run();
                Log(ok ? $"✓ {fix.name} tamam." : $"✗ {fix.name} basarisiz.");
            }
            catch (Exception ex) { Log($"✗ {fix.name}: {ex.Message}"); }
        }

        // ── Fix kaydı ve tükenme tespiti ─────────────────────────────────────
        void RecordFix(string fixId, float before, float after)
        {
            if (learning.history == null) learning.history = new List<FixRecord>();
            if (learning.exhaustedFixes == null) learning.exhaustedFixes = new List<string>();

            learning.history.Add(new FixRecord
            {
                fixId      = fixId,
                scoreBefore = before,
                scoreAfter  = after,
                timestamp  = DateTime.Now.ToString("HH:mm:ss")
            });

            // Kac kez dusuk kazanim sagladigini say
            int weakRuns = learning.history.Count(r => r.fixId == fixId && (r.scoreAfter - r.scoreBefore) < 2f);
            if (weakRuns >= 3 && !learning.exhaustedFixes.Contains(fixId))
            {
                learning.exhaustedFixes.Add(fixId);
                Log($"⚠ [{fixId}] 3 kez denendi, sonuç yok → kalıcı olarak atlandı.");
            }
        }

        // ── Temizle + yeniden kur ─────────────────────────────────────────────
        void ClearAndRebuild()
        {
            SceneBuilder.NukeSceneObjects();
            Log("Tüm _RPG_ nesneleri silindi (nükleer temizlik).");
            SceneBuilder.BuildScene();
            SceneMaterialPainter.PaintAll();
            Analyze();
        }

        // ── Fix fonksiyonlari ─────────────────────────────────────────────────
        bool FixGltfast()
        {
            string manifestPath = Path.Combine(
                Application.dataPath, "..", "Packages", "manifest.json");
            if (!File.Exists(manifestPath)) { Log("manifest.json bulunamadi!"); return false; }

            string content = File.ReadAllText(manifestPath);
            if (content.Contains("com.unity.cloud.gltfast"))
            {
                Log("glTFast zaten manifest'te var. Unity'yi yeniden acin.");
                return true;
            }

            // Paketi ekle
            content = content.Replace("\"dependencies\": {",
                "\"dependencies\": {\n    \"com.unity.cloud.gltfast\": \"6.10.0\",");
            File.WriteAllText(manifestPath, content);
            AssetDatabase.Refresh();
            Log("glTFast eklendi — Unity paketi yukleyecek.");
            return true;
        }

        bool BoostLighting()
        {
            RenderSettings.fog         = true;
            RenderSettings.fogMode     = FogMode.ExponentialSquared;
            RenderSettings.fogColor    = new Color(0.04f, 0.05f, 0.09f);
            RenderSettings.fogDensity  = 0.012f;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight= new Color(0.04f, 0.03f, 0.07f);

            // Aktif sahnede isik yetmiyorsa ekstra point light ekle
            var t = new GameObject("_RPG_AutoLight").transform;
            AddPL(t, new Vector3(  0, 6, 0), new Color(0.5f,0.1f,1.0f), 1.0f, 30f);
            AddPL(t, new Vector3( 25,12,-25), new Color(0.5f,0.1f,1.0f), 1.2f, 28f);
            AddPL(t, new Vector3(-25,12,-25), new Color(0.5f,0.1f,1.0f), 1.2f, 28f);
            AddPL(t, new Vector3(  5, 2,  5), new Color(1f,0.45f,0.10f), 2.5f, 18f);
            Log("Fog + ambient + 4 point light eklendi.");
            EditorSceneManager.MarkAllScenesDirty();
            return true;
        }

        static void AddPL(Transform parent, Vector3 pos, Color col, float intensity, float range)
        {
            var go = new GameObject($"AutoLight_{pos.x:F0}_{pos.z:F0}");
            go.transform.SetParent(parent);
            go.transform.localPosition = pos;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point; l.color = col;
            l.intensity = intensity;  l.range = range;
            l.shadows = LightShadows.Soft;
        }

        void Log(string msg) =>
            log.Add($"[{DateTime.Now:HH:mm:ss}]  {msg}");

        // ── Öğrenme JSON yardımcıları ─────────────────────────────────────────
        static LearningData LoadLearning()
        {
            string path = LearningPath();
            if (!File.Exists(path))
                return new LearningData { history = new List<FixRecord>(), exhaustedFixes = new List<string>() };
            try
            {
                var d = JsonUtility.FromJson<LearningData>(File.ReadAllText(path));
                if (d == null) return new LearningData { history = new List<FixRecord>(), exhaustedFixes = new List<string>() };
                if (d.history == null)        d.history        = new List<FixRecord>();
                if (d.exhaustedFixes == null) d.exhaustedFixes = new List<string>();
                return d;
            }
            catch
            {
                return new LearningData { history = new List<FixRecord>(), exhaustedFixes = new List<string>() };
            }
        }

        static void SaveLearning(LearningData d)
        {
            string path = LearningPath();
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonUtility.ToJson(d, true));
        }

        static string LearningPath() =>
            Path.Combine(Application.dataPath, "..", "AutopilotData", "brain_learning.json");

        // ═════════════════════════════════════════════════════════════════════
        //  UI — Editor Window Cizim
        // ═════════════════════════════════════════════════════════════════════
        void OnGUI()
        {
            InitStyles();

            // ── Baslik ─────────────────────────────────────────────────────
            DrawHeader();

            // ── Skor cemberi + progress bar ────────────────────────────────
            DrawScoreSection();

            // ── Kontroller listesi ─────────────────────────────────────────
            DrawCheckList();

            // ── Sonraki islemler (fix plan) ────────────────────────────────
            if (fixPlan.Count > 0) DrawFixPlan();

            // ── Butonlar ───────────────────────────────────────────────────
            DrawButtons();

            // ── Log ────────────────────────────────────────────────────────
            DrawLog();
        }

        void DrawHeader()
        {
            EditorGUI.DrawRect(new Rect(0, 0, position.width, 46), CDark);
            GUILayout.Space(6);
            EditorGUILayout.LabelField("★  THORNY IVY — SMART AUTOPILOT  ★", _h1, GUILayout.Height(28));
            EditorGUILayout.LabelField(
                string.IsNullOrEmpty(snap.scenePath) ? "sahne yok" : snap.scenePath,
                EditorStyles.centeredGreyMiniLabel);
            GUILayout.Space(4);
        }

        void DrawScoreSection()
        {
            float pct = Mathf.Clamp01(score / MaxScore);
            Color barCol = pct >= 0.75f ? CGreen : pct >= 0.45f ? COrange : CRed;

            EditorGUILayout.BeginVertical(EditorStyles.helpBox);

            // Buyuk skor
            var bigStyle = new GUIStyle(_h1)
            {
                fontSize = 40,
                normal   = { textColor = barCol }
            };
            string quality = pct >= 0.90f ? "MUHTEŞEM" : pct >= 0.75f ? "İYİ" :
                             pct >= 0.45f ? "GELİŞTİRİLEBİLİR" : "KRİTİK";
            EditorGUILayout.LabelField($"{score:F0}", bigStyle, GUILayout.Height(50));

            var qualStyle = new GUIStyle(EditorStyles.centeredGreyMiniLabel)
                { normal = { textColor = barCol }, fontStyle = FontStyle.Bold };
            EditorGUILayout.LabelField($"{quality}  —  {score:F0} / {MaxScore:F0} puan", qualStyle);

            // Öğrenme özeti
            if (learning != null)
            {
                int exhaustedCount = learning.exhaustedFixes != null ? learning.exhaustedFixes.Count : 0;
                var learnStyle = new GUIStyle(EditorStyles.centeredGreyMiniLabel)
                    { normal = { textColor = new Color(0.6f, 0.6f, 0.8f) } };
                EditorGUILayout.LabelField(
                    $"Zirve: {learning.peakScore:F0}  |  Döngü: {learning.totalCycles}  |  Tükenmiş: {exhaustedCount} fix",
                    learnStyle);
            }

            // Progress bar
            Rect barOuter = GUILayoutUtility.GetRect(0, 14, GUILayout.ExpandWidth(true));
            barOuter.x += 4; barOuter.width -= 8;
            EditorGUI.DrawRect(barOuter, new Color(0.12f, 0.12f, 0.14f));
            EditorGUI.DrawRect(new Rect(barOuter.x, barOuter.y, barOuter.width * pct, barOuter.height), barCol);

            GUILayout.Space(4);
            EditorGUILayout.EndVertical();
        }

        void DrawCheckList()
        {
            EditorGUILayout.LabelField("DURUM ANALIZI", _h2);
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);

            foreach (var c in checks)
            {
                EditorGUILayout.BeginHorizontal();

                // ikon
                string icon = c.OK ? "✓" : c.Partial ? "!" : "✗";
                Color  icol = c.OK ? CGreen : c.Partial ? COrange : CRed;
                EditorGUILayout.LabelField(icon,
                    new GUIStyle(EditorStyles.boldLabel) { normal = { textColor = icol }, fixedWidth = 16 },
                    GUILayout.Width(18));

                // label
                EditorGUILayout.LabelField(c.label,
                    c.OK ? EditorStyles.miniLabel
                         : new GUIStyle(EditorStyles.miniLabel) { fontStyle = FontStyle.Bold },
                    GUILayout.Width(172));

                // detay
                EditorGUILayout.LabelField(c.detail, EditorStyles.miniLabel, GUILayout.ExpandWidth(true));

                // puan
                EditorGUILayout.LabelField($"{c.score}/{c.max}",
                    new GUIStyle(EditorStyles.miniLabel)
                    {
                        alignment = TextAnchor.MiddleRight,
                        normal = { textColor = c.OK ? CGreen : COrange }
                    }, GUILayout.Width(32));

                EditorGUILayout.EndHorizontal();
            }
            EditorGUILayout.EndVertical();
        }

        void DrawFixPlan()
        {
            EditorGUILayout.LabelField("SONRAKI DUZELTMELER", _h2);
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            foreach (var f in fixPlan.Take(4))
            {
                EditorGUILayout.BeginHorizontal();
                // Tükenmiş gösterimi
                bool exhausted = learning != null && learning.exhaustedFixes != null &&
                                 learning.exhaustedFixes.Contains(f.id);
                EditorGUILayout.LabelField(exhausted ? "⚠" : "→", GUILayout.Width(14));
                EditorGUILayout.LabelField(f.name, EditorStyles.miniLabel, GUILayout.Width(180));
                EditorGUILayout.LabelField(f.description, EditorStyles.miniLabel, GUILayout.ExpandWidth(true));
                EditorGUILayout.EndHorizontal();
            }
            if (fixPlan.Count > 4)
                EditorGUILayout.LabelField($"   ... ve {fixPlan.Count - 4} adim daha",
                    EditorStyles.centeredGreyMiniLabel);
            EditorGUILayout.EndVertical();
        }

        void DrawButtons()
        {
            GUILayout.Space(4);

            // ── Ana işlem butonları ─────────────────────────────────────────
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("🔍  Analiz", GUILayout.Height(32)))
                Analyze();
            if (GUILayout.Button("â–¶  Bir Adım", GUILayout.Height(32)))
                RunNextFix();

            var allStyle = new GUIStyle(GUI.skin.button)
                { fontStyle = FontStyle.Bold, normal = { textColor = CGold } };
            if (GUILayout.Button("⚡  TÜMÜNÜ ÇALIŞTIR", allStyle, GUILayout.Height(32)))
                RunAllFixes();
            EditorGUILayout.EndHorizontal();

            // ── Yardımcı butonlar ───────────────────────────────────────────
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("â™»  Temizle + Yeniden Kur", GUILayout.Height(26)))
            {
                if (EditorUtility.DisplayDialog("Sahneyi Sifirla",
                    "Tum _RPG_ objeleri silinecek ve sahne sifirdan kurulacak.", "Evet", "Iptal"))
                    ClearAndRebuild();
            }
            if (GUILayout.Button("💾  Kaydet", GUILayout.Height(26)))
            {
                EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
                Log("Sahne kaydedildi.");
                Analyze();
            }
            if (GUILayout.Button("📋  Rapor", GUILayout.Height(26)))
                WriteReport();
            EditorGUILayout.EndHorizontal();

            // ── Otomatik Döngü Paneli ───────────────────────────────────────
            GUILayout.Space(6);
            bool loopOn = AutopilotBrainLoop.IsEnabled;
            EditorGUI.DrawRect(GUILayoutUtility.GetRect(0, 2, GUILayout.ExpandWidth(true)),
                new Color(0.25f, 0.25f, 0.30f));
            GUILayout.Space(4);

            EditorGUILayout.BeginVertical(EditorStyles.helpBox);

            EditorGUILayout.BeginHorizontal();
            // Durum ikonu + başlık
            string loopIcon  = loopOn ? "🟢" : "⚪";
            string loopLabel = loopOn
                ? $"OTOMATİK DÖNGÜ AKTİF  ·  Sonraki: {AutopilotBrainLoop.CountdownText()}"
                : "OTOMATİK DÖNGÜ KAPALI";
            var loopStyle = new GUIStyle(EditorStyles.boldLabel)
                { normal = { textColor = loopOn ? CGreen : Color.gray }, fontSize = 10 };
            EditorGUILayout.LabelField($"{loopIcon}  {loopLabel}", loopStyle, GUILayout.ExpandWidth(true));
            EditorGUILayout.EndHorizontal();

            // Slider: interval dakika
            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField("Aralık:", GUILayout.Width(40));
            _intervalMin = EditorGUILayout.Slider(_intervalMin, 5f, 120f, GUILayout.ExpandWidth(true));
            EditorGUILayout.LabelField($"{_intervalMin:F0} dk", GUILayout.Width(42));
            EditorGUILayout.EndHorizontal();

            // Aç/Kapat + Manuel tetikle
            EditorGUILayout.BeginHorizontal();
            if (loopOn)
            {
                var offStyle = new GUIStyle(GUI.skin.button) { normal = { textColor = CRed }, fontStyle = FontStyle.Bold };
                if (GUILayout.Button("⏹  DÖNGÜYÜ DURDUR", offStyle, GUILayout.Height(28)))
                {
                    AutopilotBrainLoop.SetEnabled(false);
                    Log("Otomatik döngü durduruldu.");
                }
            }
            else
            {
                var onStyle = new GUIStyle(GUI.skin.button) { normal = { textColor = CPurple }, fontStyle = FontStyle.Bold };
                if (GUILayout.Button($"â–¶  DÖNGÜYÜ BAŞLAT  ({_intervalMin:F0} dk)", onStyle, GUILayout.Height(28)))
                {
                    AutopilotBrainLoop.SetEnabled(true, _intervalMin);
                    Log($"Otomatik döngü başlatıldı — her {_intervalMin:F0} dakikada bir çalışacak.");
                }
            }

            if (GUILayout.Button("â–¶ Şimdi Çalıştır", GUILayout.Height(28), GUILayout.Width(120)))
            {
                Log("[MANUAL] Manuel döngü tetiklendi.");
                AutoRun();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.EndVertical();
        }

        void DrawLog()
        {
            GUILayout.Space(4);
            EditorGUILayout.LabelField("LOG", _h2);
            logScroll = EditorGUILayout.BeginScrollView(logScroll, GUILayout.ExpandHeight(true));
            foreach (var line in Enumerable.Reverse(log).Take(60))
            {
                Color lc = line.Contains("✓") ? CGreen
                         : line.Contains("✗") ? CRed
                         : line.Contains("[AUTO]")  ? CPurple
                         : line.Contains("[MANUAL]") ? CBlue
                         : line.Contains("â–¶") ? CBlue
                         : line.Contains("━")  ? CGold
                         : Color.gray;
                EditorGUILayout.LabelField(line,
                    new GUIStyle(EditorStyles.miniLabel) { normal = { textColor = lc } });
            }
            EditorGUILayout.EndScrollView();
        }

        // ── Rapor yaz ─────────────────────────────────────────────────────────
        void WriteReport()
        {
            string dir = Path.Combine(Application.dataPath, "..", "AutopilotData");
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, "brain_report.md");

            var sb = new System.Text.StringBuilder();
            sb.AppendLine("# Thorny Ivy — Autopilot Brain Raporu");
            sb.AppendLine($"Tarih: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            sb.AppendLine($"**Toplam Skor: {score:F0}/100**");
            if (learning != null)
            {
                sb.AppendLine($"**Zirve Skor: {learning.peakScore:F0}  |  Toplam Döngü: {learning.totalCycles}**");
                if (learning.exhaustedFixes != null && learning.exhaustedFixes.Count > 0)
                    sb.AppendLine($"**Tükenmiş Fixler:** {string.Join(", ", learning.exhaustedFixes)}");
            }
            sb.AppendLine();
            sb.AppendLine("## Durum Analizi");
            foreach (var c in checks)
            {
                string bullet = c.OK ? "✅" : c.Partial ? "⚠️" : "❌";
                sb.AppendLine($"{bullet} **{c.label}** — {c.detail} ({c.score}/{c.max})");
            }
            sb.AppendLine();
            sb.AppendLine("## Gereken Duzeltmeler");
            foreach (var f in fixPlan)
                sb.AppendLine($"- **{f.name}**: {f.description}");

            File.WriteAllText(path, sb.ToString(), System.Text.Encoding.UTF8);
            Log($"Rapor yazildi: {path}");
            AssetDatabase.Refresh();
        }

        // ── GUIStyle init ─────────────────────────────────────────────────────
        void InitStyles()
        {
            if (_h1 != null) return;
            _h1 = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize  = 14,
                alignment = TextAnchor.MiddleCenter,
                normal    = { textColor = CGold }
            };
            _h2 = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize  = 10,
                normal    = { textColor = new Color(0.6f, 0.6f, 0.7f) }
            };
            _mono = new GUIStyle(EditorStyles.miniLabel)
            {
                font = (Font)Resources.Load("Fonts/LiberationMono-Regular")
            };
        }
    }
}
#endif

