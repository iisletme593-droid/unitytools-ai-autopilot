#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  THORNY IVY â€” SCENE BUILDER  v4
    //  Referans gÃ¶rseller: 816ea051, 0f1450a9, ba4ec276, fd3cd05d, HF_GAME_AI_07
    //
    //  Sahne dÃ¼zeni (oyuncu Z=0, kale Z=+85, kuzey yÃ¶nÃ¼ +Z):
    //    Z=  0   Oyuncu baÅŸlangÄ±cÄ±, kamera arkada (Z=-14)
    //    Z=+15   KÃ¶y kapÄ±sÄ± â€” sol bÃ¼yÃ¼k kulÃ¼be / saÄŸ kÃ¼Ã§Ã¼k kulÃ¼be
    //    Z=+10   Kampfire (yol sol kenarÄ±)
    //    Z=Â±10â€”80 Pine + Fir ormanÄ± (yolun iki yanÄ±nda ÅŸerit)
    //    Z=+85   Gotik kale â€” karanlÄ±k taÅŸ, ince kuleler, sihirli Ä±ÅŸÄ±n
    //
    //  Atmosfer: koyu gotik â€” yoÄŸun mavi-gri sis, neredeyse gece ortamÄ±
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    [InitializeOnLoad]
    public static class SceneBuilder
    {
        const string DoneKey   = "ThornyIvy_SceneBuilder_v6";
        const string AssetDest = "Assets/FantasyRPG";

        static readonly string PackRoot = Path.GetFullPath(
            Path.Combine(Application.dataPath, "../../Fantasy_RPG_Class_Item_Pack"));

        static readonly (string src, string dst)[] AssetFolders =
        {
            ("Meshes_Real",               "Models/Sketchfab"),
            ("Meshes_PolyHaven",          "Models/PolyHaven"),
            ("Meshes_AI",                 "Models/ShapE"),
            ("Assets_AmbientCG/HDRIs",    "HDRIs"),
            ("Assets_AmbientCG/Textures", "Textures"),
        };

        static SceneBuilder()
        {
            if (!AutopilotExecutionMode.ShouldRunAutomatic("SceneBuilder.ImportAssets")) return;
            if (SessionState.GetBool(DoneKey, false)) return;
            EditorApplication.delayCall += AutoRun;
        }

        static void AutoRun()
        {
            if (SessionState.GetBool(DoneKey, false)) return;
            SessionState.SetBool(DoneKey, true);
            ImportAssets();
        }

        // â”€â”€ 1. Asset Import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        [MenuItem("Tools/Autopilot/1 - Import All Assets")]
        public static void ImportAssets()
        {
            if (!Directory.Exists(PackRoot))
            {
                Debug.LogWarning($"[SceneBuilder] Pack klasoru bulunamadi: {PackRoot}");
                return;
            }
            int copied = 0;
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (var (src, dst) in AssetFolders)
                {
                    string srcPath = Path.Combine(PackRoot, src);
                    if (!Directory.Exists(srcPath)) continue;
                    string dstPath = Path.Combine(Application.dataPath, dst);
                    Directory.CreateDirectory(dstPath);
                    foreach (string file in Directory.GetFiles(srcPath, "*", SearchOption.AllDirectories))
                    {
                        string ext = Path.GetExtension(file).ToLower();
                        if (!IsImportable(ext)) continue;
                        string rel      = file.Substring(srcPath.Length + 1);
                        string destFile = Path.Combine(dstPath, rel);
                        Directory.CreateDirectory(Path.GetDirectoryName(destFile));
                        if (!File.Exists(destFile)) { File.Copy(file, destFile); copied++; }
                    }
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            AssetDatabase.Refresh();
            Debug.Log($"[SceneBuilder] {copied} asset kopyalandi -> Assets/FantasyRPG/");
        }

        static bool IsImportable(string ext) =>
            ext is ".glb" or ".fbx" or ".obj" or ".png" or ".jpg" or ".hdr" or ".exr";

        // â”€â”€ NÃ¼kleer temizlik â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        public static void NukeSceneObjects()
        {
            var all   = Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include);
            var roots = new HashSet<GameObject>();

            foreach (var g in all)
            {
                if (g == null) continue;
                var root = g.transform.root.gameObject;
                if (g.name.StartsWith("_RPG_")) { roots.Add(root); continue; }
                if (root == g && IsStrayObject(g.name)) roots.Add(root);
            }

            var safeCamRoots = new HashSet<GameObject>(
                Object.FindObjectsByType<Camera>(FindObjectsInactive.Include)
                      .Select(c => c.transform.root.gameObject));
            var playerGo = GameObject.FindGameObjectWithTag("Player");

            foreach (var r in roots)
            {
                if (r == null) continue;
                if (safeCamRoots.Contains(r)) continue;
                if (playerGo != null && r == playerGo.transform.root.gameObject) continue;
                Undo.DestroyObjectImmediate(r);
            }
        }

        static bool IsStrayObject(string name) =>
            name is "Cube" or "Cylinder" or "Plane" or "Sphere" or "Capsule" or "Quad"
                 or "CampFire_Scene" or "CampFireLight" or "Directional_Sun" ||
            name.StartsWith("GameObject") ||
            name.StartsWith("New Game Object") ||
            name.StartsWith("AutoLight_");

        // â”€â”€ 2. Sahne Kur â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        [MenuItem("Tools/Autopilot/2 - Build Fantasy Scene")]
        public static void BuildScene()
        {
            NukeSceneObjects();

            var rng  = new System.Random(42);
            var root = new GameObject("_RPG_Scene");
            Undo.RegisterCreatedObjectUndo(root, "Build RPG Scene");

            // SÄ±ralÄ± aÅŸamalar â€” Ã¶nce zemin/atmosfer, sonra nesneler
            BuildTerrain(root.transform);
            BuildAtmosphere();
            BuildCastle(root.transform);
            BuildVillageGateway(root.transform);
            BuildForest(root.transform, rng);
            BuildDungeonRoom(root.transform);
            BuildEnemyZones(root.transform, rng);
            BuildLights(root.transform);

            EnsureCameraAndPlayer();

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            Debug.Log("[SceneBuilder v4] Sahne kuruldu. Referans: 816ea051 / 0f1450a9.");
            SceneView.lastActiveSceneView?.Frame(new Bounds(new Vector3(0, 5, 40), Vector3.one * 120f), false);
        }

        // â”€â”€ Atmosfer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // Referans: 816ea051 / 0f1450a9 â€” koyu gotik, yoÄŸun sis, geceye yakÄ±n
        static void BuildAtmosphere()
        {
            RenderSettings.ambientMode  = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.022f, 0.028f, 0.052f);  // neredeyse siyah-mavi

            RenderSettings.fog        = true;
            RenderSettings.fogMode    = FogMode.ExponentialSquared;
            RenderSettings.fogColor   = new Color(0.28f, 0.30f, 0.38f);       // koyu mavi-gri sis
            RenderSettings.fogDensity = 0.038f;                                // yoÄŸun â€” kale uzakta kaybolsun

            RenderSettings.reflectionIntensity = 0.20f;
        }

        // â”€â”€ Zemin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        [MenuItem("Tools/Autopilot/7 - Rebuild Terrain")]
        public static void RebuildTerrainTextured()
        {
            var old = GameObject.Find("_RPG_Terrain");
            if (old != null) Undo.DestroyObjectImmediate(old);
            var sceneRoot = GameObject.Find("_RPG_Scene");
            Transform parent = sceneRoot != null ? sceneRoot.transform : null;
            if (parent == null) { var r = new GameObject("_RPG_Scene"); parent = r.transform; }
            BuildTerrain(parent);
            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        }

        static void BuildTerrain(Transform parent)
        {
            var t = new GameObject("_RPG_Terrain").transform;
            t.SetParent(parent);

            // Ana zemin â€” referans gÃ¶rsellerde: koyu gri-yeÅŸil, yoÄŸun sisli ortam
            // 200Ã—200m merkez (0,0,0) â€” oyuncu Z=0, kale Z=85 iÃ§inde kalÄ±r
            var grass = GameObject.CreatePrimitive(PrimitiveType.Plane);
            grass.name = "_RPG_GrassGround";
            grass.transform.SetParent(t);
            grass.transform.localPosition = new Vector3(0f, 0f, 45f);  // sahneyi dengele
            grass.transform.localScale    = new Vector3(20f, 1f, 20f); // 200Ã—200m
            ApplyPbrGroundMat(grass, "Grass007", "Ground",
                tiling: 40f, smoothness: 0.06f,
                fallback: new Color(0.025f, 0.065f, 0.015f)); // koyu gri-yeÅŸil (referans atmosferi)

            // Merkez yol â€” oyuncudan kaleye kadar uzanan toprak/Ã§amur yol
            // Z=-5 â†’ Z=90, yani 95m uzunluk, 5.5m geniÅŸlik
            var path = GameObject.CreatePrimitive(PrimitiveType.Plane);
            path.name = "_RPG_DirtPath";
            path.transform.SetParent(t);
            path.transform.localPosition = new Vector3(0f, 0.01f, 42.5f); // merkez
            path.transform.localScale    = new Vector3(0.55f, 1f, 9.5f);  // 5.5m Ã— 95m
            ApplyPbrGroundMat(path, "Ground054", "Ground",
                tiling: 18f, smoothness: 0.14f,
                fallback: new Color(0.08f, 0.062f, 0.040f)); // koyu Ã§amurlu toprak
        }

        // â”€â”€ Kale â€” Referans: koyu gotik taÅŸ, ince kuleler, sihirli Ä±ÅŸÄ±n â”€â”€â”€â”€â”€â”€
        // Konum: Z=+85, oyuncu yolun sonunda kaleyi gÃ¶rÃ¼r
        static void BuildCastle(Transform parent)
        {
            var t = new GameObject("_RPG_Castle").transform;
            t.SetParent(parent);
            t.localPosition = new Vector3(0f, 0f, 85f);

            // ModularFort GLB â€” ana kale yapÄ±sÄ± (varsa kullan)
            var fort = SpawnGLB(t, "ModularFort", new Vector3(0f, 0f, 0f),
                                 Vector3.zero, Vector3.one, targetMeters: 22f);

            // Ana gÃ¶vde primitifi (fort yoksa)
            var keep = GameObject.CreatePrimitive(PrimitiveType.Cube);
            keep.name = "_RPG_CastleKeep";
            keep.transform.SetParent(t);
            keep.transform.localPosition = new Vector3(0f, 9f, 0f);
            keep.transform.localScale    = new Vector3(20f, 18f, 14f);
            ApplyPbrGroundMat(keep, "Concrete042A", "Stone",
                tiling: 3f, smoothness: 0.14f,
                fallback: new Color(0.09f, 0.08f, 0.07f)); // siyah-koyu taÅŸ
            if (fort != null) keep.GetComponent<MeshRenderer>().enabled = false;

            // Ã–n duvar + beden duvarlarÄ±
            BuildWall(t, "_RPG_Wall_S", new Vector3( 0f, 4f, -10f), new Vector3(24f, 8f, 1.0f));
            BuildWall(t, "_RPG_Wall_W", new Vector3(-12f, 4f, 0f),  new Vector3(1.0f, 8f, 20f));
            BuildWall(t, "_RPG_Wall_E", new Vector3( 12f, 4f, 0f),  new Vector3(1.0f, 8f, 20f));

            // Koyu gotik kuleler â€” 4 kÃ¶ÅŸe + merkez (en yÃ¼ksek)
            SpawnDarkTower(t, new Vector3(-12f, 0f, -10f), 26f, 2.8f);
            SpawnDarkTower(t, new Vector3( 12f, 0f, -10f), 26f, 2.8f);
            SpawnDarkTower(t, new Vector3(-12f, 0f,  10f), 22f, 2.4f);
            SpawnDarkTower(t, new Vector3( 12f, 0f,  10f), 22f, 2.4f);
            SpawnDarkTower(t, new Vector3(  0f, 0f,   0f), 34f, 3.8f); // merkez kule

            // KapÄ±
            var gate = SpawnGLB(t, "IronGate",   new Vector3(0f, 0f, -10f), Vector3.zero, Vector3.one, targetMeters: 4.5f)
                    ?? SpawnGLB(t, "CastleDoor", new Vector3(0f, 0f, -10f), Vector3.zero, Vector3.one, targetMeters: 4.5f);
            if (gate == null)
            {
                var gb = GameObject.CreatePrimitive(PrimitiveType.Cube);
                gb.name = "_RPG_CastleGate";
                gb.transform.SetParent(t);
                gb.transform.SetLocalPositionAndRotation(new Vector3(0f, 2.8f, -10f), Quaternion.identity);
                gb.transform.localScale = new Vector3(4.5f, 5.5f, 0.5f);
                ApplyMat(gb, new Color(0.06f, 0.05f, 0.04f)); // koyu demir kapÄ±
            }

            // Sihirli Ä±ÅŸÄ±n â€” referans gÃ¶rsellerin hepsinde var (ba4ec276, 0f1450a9, 816ea051)
            BuildMagicBeam(t, new Vector3(0f, 34f, 0f));
        }

        // Koyu gotik kule (referans: karanlÄ±k gotik kale silueti)
        static void SpawnDarkTower(Transform parent, Vector3 pos, float height, float radius)
        {
            var body = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            body.name = "_RPG_Tower";
            body.transform.SetParent(parent);
            body.transform.localPosition = pos + Vector3.up * (height * 0.5f);
            body.transform.localScale    = new Vector3(radius * 2f, height * 0.5f, radius * 2f);
            ApplyPbrGroundMat(body, "Concrete042A", "Stone",
                tiling: 2f, smoothness: 0.12f,
                fallback: new Color(0.08f, 0.07f, 0.06f)); // siyah taÅŸ

            // Sivri kule tepesi â€” koyu mor-siyah (referans: gotik spire)
            var spire = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            spire.name = "_RPG_TowerSpire";
            spire.transform.SetParent(parent);
            spire.transform.localPosition = pos + Vector3.up * (height + 4f);
            spire.transform.localScale    = new Vector3(radius * 1.6f, 4.5f, radius * 1.6f);
            ApplyMat(spire, new Color(0.05f, 0.04f, 0.07f)); // koyu mor-siyah
        }

        static void BuildWall(Transform parent, string wallName, Vector3 pos, Vector3 scale)
        {
            var w = GameObject.CreatePrimitive(PrimitiveType.Cube);
            w.name = wallName;
            w.transform.SetParent(parent);
            w.transform.localPosition = pos;
            w.transform.localScale    = scale;
            ApplyPbrGroundMat(w, "Concrete042A", "Stone",
                tiling: 3f, smoothness: 0.12f,
                fallback: new Color(0.09f, 0.08f, 0.07f)); // koyu kale taÅŸÄ±
        }

        // Sihirli Ä±ÅŸÄ±n â€” kale tepesinden gÃ¶kyÃ¼zÃ¼ne (referans tÃ¼m gÃ¶rsellerde)
        static void BuildMagicBeam(Transform parent, Vector3 localPos)
        {
            var beam = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            beam.name = "_RPG_MagicBeam";
            beam.transform.SetParent(parent);
            beam.transform.localPosition = localPos;
            beam.transform.localScale    = new Vector3(0.35f, 120f, 0.35f); // ince, Ã§ok uzun

            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard");
            var mat = new Material(shader) { name = "_RPG_Mat_MagicBeam" };
            Color beamAlbedo = new Color(0.75f, 0.55f, 1.0f); // soluk mor-beyaz
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", beamAlbedo);
            if (mat.HasProperty("_Color"))     mat.SetColor("_Color",     beamAlbedo);
            Color emColor = new Color(2.2f, 1.2f, 3.0f); // yoÄŸun mor emisyon
            if (mat.HasProperty("_EmissiveColor")) mat.SetColor("_EmissiveColor", emColor);
            if (mat.HasProperty("_EmissionColor")) mat.SetColor("_EmissionColor", emColor);
            if (mat.HasProperty("_EmissiveIntensity")) mat.SetFloat("_EmissiveIntensity", 6f);
            mat.EnableKeyword("_EMISSION");
            beam.GetComponent<MeshRenderer>().sharedMaterial = mat;
        }

        // â”€â”€ KÃ¶y KapÄ±sÄ± â€” Referans: 816ea051 / 0f1450a9 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // Yolun iki yanÄ±nda iki yapÄ±: sol bÃ¼yÃ¼k kulÃ¼be + saÄŸ kÃ¼Ã§Ã¼k kulÃ¼be
        // Kampfire + fenerler sÄ±cak Ä±ÅŸÄ±k kaynaÄŸÄ±
        static void BuildVillageGateway(Transform parent)
        {
            var t = new GameObject("_RPG_Village").transform;
            t.SetParent(parent);

            BuildLeftCabin(t);    // bÃ¼yÃ¼k log kulÃ¼be (referans: 816ea051 sol)
            BuildRightOutpost(t); // kÃ¼Ã§Ã¼k kulÃ¼be/bekÃ§i kulÃ¼besi (referans: 816ea051 saÄŸ)
        }

        static void BuildLeftCabin(Transform parent)
        {
            var t = new GameObject("_RPG_LeftCabin").transform;
            t.SetParent(parent);
            t.localPosition = new Vector3(-9f, 0f, 18f);

            // Ana gÃ¶vde â€” bÃ¼yÃ¼k ahÅŸap kulÃ¼be
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "_RPG_Cabin";
            body.transform.SetParent(t);
            body.transform.localPosition = new Vector3(0f, 2.8f, 0f);
            body.transform.localScale    = new Vector3(7f, 5.5f, 6f);
            ApplyPbrGroundMat(body, "WoodFloor025", "Wood",
                tiling: 2f, smoothness: 0.15f,
                fallback: new Color(0.22f, 0.14f, 0.08f)); // koyu ahÅŸap

            // Ã‡atÄ± â€” geniÅŸ, koyu
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "_RPG_CabinRoof";
            roof.transform.SetParent(t);
            roof.transform.localPosition = new Vector3(0f, 6.4f, 0f);
            roof.transform.localScale    = new Vector3(8.2f, 2.2f, 7.2f);
            ApplyMat(roof, new Color(0.11f, 0.09f, 0.08f));

            // Baca â€” koyu taÅŸ baca
            var chimney = GameObject.CreatePrimitive(PrimitiveType.Cube);
            chimney.name = "_RPG_Chimney";
            chimney.transform.SetParent(t);
            chimney.transform.localPosition = new Vector3(2f, 9f, 1f);
            chimney.transform.localScale    = new Vector3(0.85f, 3.2f, 0.85f);
            ApplyMat(chimney, new Color(0.14f, 0.12f, 0.10f));

            // Veranda
            var porch = GameObject.CreatePrimitive(PrimitiveType.Cube);
            porch.name = "_RPG_Porch";
            porch.transform.SetParent(t);
            porch.transform.localPosition = new Vector3(0f, 0.22f, -4f);
            porch.transform.localScale    = new Vector3(5.5f, 0.44f, 2.5f);
            ApplyMat(porch, new Color(0.18f, 0.12f, 0.07f));

            // Basamak
            var step = GameObject.CreatePrimitive(PrimitiveType.Cube);
            step.name = "_RPG_Step";
            step.transform.SetParent(t);
            step.transform.localPosition = new Vector3(0f, 0.1f, -5.4f);
            step.transform.localScale    = new Vector3(3.5f, 0.2f, 1f);
            ApplyMat(step, new Color(0.20f, 0.17f, 0.13f));

            // StoneFire â€” kulÃ¼be Ã¶nÃ¼nde, yolun sol kenarÄ±nda
            var fire = SpawnGLB(t, "StoneFire", new Vector3(4f, 0f, -5.5f),
                                 Vector3.zero, Vector3.one, targetMeters: 0.85f);
            if (fire == null)
            {
                var cf = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                cf.name = "_RPG_CampFire";
                cf.transform.SetParent(t);
                cf.transform.localPosition = new Vector3(4f, 0.12f, -5.5f);
                cf.transform.localScale    = new Vector3(0.75f, 0.14f, 0.75f);
                ApplyMat(cf, new Color(0.70f, 0.24f, 0.03f));
            }
            else fire.name = "_RPG_CampFire";

            // Fener â€” kapÄ± yanÄ±nda (referans: 816ea051 sol kulÃ¼bede fener)
            SpawnGLB(t, "Lantern", new Vector3(-3.2f, 2.6f, -3.2f),
                     Vector3.zero, Vector3.one, targetMeters: 0.32f);

            // KulÃ¼be yanÄ± proplar â€” fÄ±Ã§Ä±, sandÄ±k, kova
            SpawnGLB(t, "Barrel1",       new Vector3(-4f, 0f, -1.5f), new Vector3(0f, 25f, 0f), Vector3.one, targetMeters: 0.80f);
            SpawnGLB(t, "WoodenCrate1",  new Vector3(-4f, 0f, -2.8f), Vector3.zero,              Vector3.one, targetMeters: 0.60f);
            SpawnGLB(t, "WoodenBucket1", new Vector3( 3f, 0f, -2.2f), Vector3.zero,              Vector3.one, targetMeters: 0.35f);
            SpawnGLB(t, "WickerBasket",  new Vector3( 3.5f, 0f, -1f), new Vector3(0f, 40f, 0f),  Vector3.one, targetMeters: 0.40f);

            // Kaya â€” kulÃ¼be kÃ¶ÅŸesinde dekor
            SpawnGLB(t, "Boulder1",   new Vector3(-4f, 0f,  2.5f), new Vector3(0f, 45f, 0f), Vector3.one, targetMeters: 0.70f);
            SpawnGLB(t, "RockMossSet",new Vector3( 4f, 0f,  2.0f), new Vector3(0f, 20f, 0f), Vector3.one, targetMeters: 0.55f);
        }

        static void BuildRightOutpost(Transform parent)
        {
            var t = new GameObject("_RPG_RightOutpost").transform;
            t.SetParent(parent);
            t.localPosition = new Vector3(10f, 0f, 22f);

            // Ana gÃ¶vde â€” kÃ¼Ã§Ã¼k bekÃ§i kulÃ¼besi
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "_RPG_Shed";
            body.transform.SetParent(t);
            body.transform.localPosition = new Vector3(0f, 1.9f, 0f);
            body.transform.localScale    = new Vector3(4.5f, 3.8f, 4.5f);
            ApplyPbrGroundMat(body, "WoodFloor025", "Wood",
                tiling: 1.5f, smoothness: 0.15f,
                fallback: new Color(0.19f, 0.12f, 0.07f));

            // Ã‡atÄ±
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "_RPG_ShedRoof";
            roof.transform.SetParent(t);
            roof.transform.localPosition = new Vector3(0f, 4.3f, 0f);
            roof.transform.localScale    = new Vector3(5.8f, 1.6f, 5.8f);
            ApplyMat(roof, new Color(0.10f, 0.09f, 0.08f));

            // Fener direÄŸi â€” referans 816ea051: saÄŸda asÄ±lÄ± fener
            var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            pole.name = "_RPG_LanternPole";
            pole.transform.SetParent(t);
            pole.transform.localPosition = new Vector3(-3f, 2.2f, -3f);
            pole.transform.localScale    = new Vector3(0.12f, 2.2f, 0.12f);
            ApplyMat(pole, new Color(0.12f, 0.10f, 0.08f));

            var shedLantern = SpawnGLB(t, "WoodenLantern", new Vector3(-3f, 4.5f, -3f), Vector3.zero, Vector3.one, targetMeters: 0.32f);
            if (shedLantern == null)
                SpawnGLB(t, "Lantern", new Vector3(-3f, 4.5f, -3f), Vector3.zero, Vector3.one, targetMeters: 0.32f);

            SpawnGLB(t, "TreasureChest", new Vector3( 1.8f, 0f, -1.5f), new Vector3(0f, 30f, 0f), Vector3.one, targetMeters: 0.52f);
            SpawnGLB(t, "WineBarrel",    new Vector3(-1.5f, 0f,  1.5f), new Vector3(0f, 15f, 0f), Vector3.one, targetMeters: 0.70f);
            SpawnGLB(t, "Rock9",         new Vector3( 2.5f, 0f,  2.0f), Vector3.zero,              Vector3.one, targetMeters: 0.50f);
        }

        // â”€â”€ Orman â€” Referans: yolun iki yanÄ±nda yoÄŸun ÅŸerit orman â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // PineTree + FirTree + IslandTree + DeadTreeTrunk karÄ±ÅŸÄ±mÄ±
        // Kayalar, stump ve kÃ¼tÃ¼kler zemin dekoru
        static void BuildForest(Transform parent, System.Random rng)
        {
            var t = new GameObject("_RPG_Forest").transform;
            t.SetParent(parent);

            string[] conifers = { "PineTree", "FirTree", "IslandTree" };
            string[] dead     = { "DeadTreeTrunk" };
            string[] stumps   = { "TreeStump1", "TreeStump2" };
            string[] rocks    = { "Boulder1", "Rock7", "Rock9", "RockFace1", "RockMossSet" };

            // Sol orman ÅŸeridi (X: -10 â†’ -58, Z: +2 â†’ +82)
            PlaceInStrip(t, conifers, rng, -58f, -10f, 2f,  82f, 38, 12f, 0.80f, 1.70f);
            PlaceInStrip(t, dead,     rng, -42f, -10f, 5f,  78f, 12,  8f, 0.70f, 1.25f);
            PlaceInStrip(t, stumps,   rng, -55f, -10f, 2f,  80f, 12, 0.7f,0.55f, 1.20f);
            PlaceInStrip(t, rocks,    rng, -58f,  -8f, 0f,  82f, 18, 0.9f, 0.45f, 1.50f);

            // SaÄŸ orman ÅŸeridi (X: +10 â†’ +58, Z: +2 â†’ +82)
            PlaceInStrip(t, conifers, rng,  10f,  58f, 2f,  82f, 38, 12f, 0.80f, 1.70f);
            PlaceInStrip(t, dead,     rng,  10f,  42f, 5f,  78f, 12,  8f, 0.70f, 1.25f);
            PlaceInStrip(t, stumps,   rng,  10f,  55f, 2f,  80f, 12, 0.7f,0.55f, 1.20f);
            PlaceInStrip(t, rocks,    rng,   8f,  58f, 0f,  82f, 18, 0.9f, 0.45f, 1.50f);

            // Yol kenarÄ± yakÄ±n aÄŸaÃ§lar (Z=+5 to +15 arasÄ± yoÄŸun)
            PlaceInStrip(t, conifers, rng, -22f, -10f,  5f, 15f, 8, 12f, 0.85f, 1.40f);
            PlaceInStrip(t, conifers, rng,  10f,  22f,  5f, 15f, 8, 12f, 0.85f, 1.40f);

            // Kale yakÄ±nÄ± (Z=+68 to +82) â€” kaleyi Ã§erÃ§eveleyen aÄŸaÃ§lar
            PlaceInStrip(t, conifers, rng, -30f, -10f, 68f, 82f, 8, 14f, 1.00f, 1.80f);
            PlaceInStrip(t, conifers, rng,  10f,  30f, 68f, 82f, 8, 14f, 1.00f, 1.80f);
            PlaceInStrip(t, dead,     rng, -25f, -10f, 65f, 82f, 4,  9f, 0.80f, 1.20f);
            PlaceInStrip(t, dead,     rng,  10f,  25f, 65f, 82f, 4,  9f, 0.80f, 1.20f);
        }

        static void PlaceInStrip(Transform parent, string[] hints, System.Random rng,
                                  float xMin, float xMax, float zMin, float zMax,
                                  int count, float targetM, float scaleMin, float scaleMax)
        {
            for (int i = 0; i < count; i++)
            {
                float x    = xMin + (float)rng.NextDouble() * (xMax - xMin);
                float z    = zMin + (float)rng.NextDouble() * (zMax - zMin);
                float ry   = (float)rng.NextDouble() * 360f;
                float mult = scaleMin + (float)rng.NextDouble() * (scaleMax - scaleMin);
                string hint = hints[rng.Next(hints.Length)];
                SpawnGLB(parent, hint, new Vector3(x, 0f, z),
                         new Vector3(0f, ry, 0f), Vector3.one * mult, targetMeters: targetM);
            }
        }

        // PlaceInRingNorm: DÃ¼ÅŸman/Ã§ember yerleÅŸimi iÃ§in hÃ¢lÃ¢ kullanÄ±lÄ±yor
        static void PlaceInRingNorm(Transform parent, string[] hints, System.Random rng,
                                     float rMin, float rMax, int count,
                                     float targetM, float scaleMin, float scaleMax)
        {
            for (int i = 0; i < count; i++)
            {
                float angle  = (float)rng.NextDouble() * 360f * Mathf.Deg2Rad;
                float radius = rMin + (float)rng.NextDouble() * (rMax - rMin);
                var   pos    = new Vector3(Mathf.Cos(angle) * radius, 0f, Mathf.Sin(angle) * radius);
                float ry     = (float)rng.NextDouble() * 360f;
                float mult   = scaleMin + (float)rng.NextDouble() * (scaleMax - scaleMin);
                string hint  = hints[rng.Next(hints.Length)];
                SpawnGLB(parent, hint, pos + new Vector3(0f, 0f, 42f), // dÃ¼ÅŸman Ã§emberi sahne ortasÄ±nda
                         new Vector3(0f, ry, 0f), Vector3.one * mult, targetMeters: targetM);
            }
        }

        // â”€â”€ Dungeon â€” YeraltÄ±nda (Y=-8), avluyla Ã§akÄ±ÅŸmaz â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void BuildDungeonRoom(Transform parent)
        {
            var t = new GameObject("_RPG_Dungeon").transform;
            t.SetParent(parent);
            t.localPosition = new Vector3(35f, -8f, 40f); // kale saÄŸÄ±nda, yeraltÄ±

            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "_RPG_DungeonFloor";
            floor.transform.SetParent(t);
            floor.transform.localScale = new Vector3(2f, 1f, 2f);
            ApplyPbrGroundMat(floor, "Bricks101", "Stone",
                tiling: 6f, smoothness: 0.20f,
                fallback: new Color(0.18f, 0.16f, 0.13f));

            SpawnGLB(t, "GothicBed",      new Vector3(-5f, 0f, -5f), new Vector3(0f,   0f, 0f), Vector3.one, targetMeters: 2.0f);
            SpawnGLB(t, "TreasureChest",  new Vector3( 7f, 0f,  7f), new Vector3(0f,  45f, 0f), Vector3.one, targetMeters: 0.65f);
            SpawnGLB(t, "Barrel1",        new Vector3( 8f, 0f, -6f), Vector3.zero,               Vector3.one, targetMeters: 0.80f);
            SpawnGLB(t, "Lantern",        new Vector3( 9f, 1.4f, 9f),Vector3.zero,               Vector3.one, targetMeters: 0.40f);
            SpawnGLB(t, "GothicCabinet",  new Vector3(-7f, 0f,  6f), new Vector3(0f, 180f, 0f),  Vector3.one, targetMeters: 2.2f);
            SpawnGLB(t, "WornBookshelf",  new Vector3(-7f, 0f, -7f), new Vector3(0f,  90f, 0f),  Vector3.one, targetMeters: 1.8f);

            AddPointLight(t, new Vector3(0f, 0.8f, 8f), new Color(1f, 0.45f, 0.08f), 3f, 14f);
        }

        // â”€â”€ DÃ¼ÅŸman ZonlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void BuildEnemyZones(Transform parent, System.Random rng)
        {
            var t = new GameObject("_RPG_Enemies").transform;
            t.SetParent(parent);

            SpawnEnemyRing(t, rng, 18f, 30f, 4, 1,  1,  3, "Zone1_Acolyte");
            SpawnEnemyRing(t, rng, 32f, 45f, 6, 2,  4,  6, "Zone2_Forest");
            SpawnEnemyRing(t, rng, 50f, 62f, 4, 3,  7, 10, "Zone3_Elite");
            SpawnEnemyRing(t, rng, 68f, 76f, 2, 4, 12, 15, "Zone4_Boss");
        }

        static void SpawnEnemyRing(Transform parent, System.Random rng,
            float innerR, float outerR, int count, int tier, int levelMin, int levelMax, string name)
        {
            Color[] tierColors = {
                new Color(0.3f, 0.6f, 0.3f),
                new Color(0.6f, 0.5f, 0.1f),
                new Color(0.7f, 0.2f, 0.1f),
                new Color(0.5f, 0.0f, 0.7f),
            };
            for (int i = 0; i < count; i++)
            {
                float angle  = (float)rng.NextDouble() * Mathf.PI * 2f;
                float radius = innerR + (float)rng.NextDouble() * (outerR - innerR);
                var   pos    = new Vector3(Mathf.Cos(angle) * radius, 0f,
                                           42f + Mathf.Sin(angle) * radius * 0.5f); // dÃ¼ÅŸmanlar yol boyunca
                float ry = (float)rng.NextDouble() * 360f;

                var existing = SpawnEnemyPrefab(parent, pos, tier);
                if (existing != null)
                {
                    existing.name = $"_RPG_{name}_{i + 1:D2}";
                    existing.transform.localEulerAngles = new Vector3(0f, ry, 0f);
                    var ai = existing.GetComponent<Gameplay.EnemyAIController>();
                    if (ai != null) { ai.enemyTier = tier; ai.enemyLevel = levelMin + rng.Next(levelMax - levelMin + 1); }
                }
                else
                {
                    var proxy = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                    proxy.name = $"_RPG_{name}_{i + 1:D2}_Proxy";
                    proxy.transform.SetParent(parent);
                    proxy.transform.SetLocalPositionAndRotation(pos, Quaternion.Euler(0f, ry, 0f));
                    proxy.transform.localScale = Vector3.one * (0.9f + tier * 0.25f);
                    ApplyMat(proxy, tierColors[Mathf.Clamp(tier - 1, 0, 3)]);
                    var ai = proxy.AddComponent<Gameplay.EnemyAIController>();
                    ai.enemyTier  = tier;
                    ai.enemyLevel = levelMin + rng.Next(levelMax - levelMin + 1);
                }
            }
        }

        static GameObject SpawnEnemyPrefab(Transform parent, Vector3 pos, int tier)
        {
            string[][] tierHints = {
                new[]{ "RootAcolyte", "Enemy_01", "EnemyWeak"   },
                new[]{ "BeastAnother","Enemy_02", "EnemyMedium" },
                new[]{ "Behemoth",    "Enemy_03", "EnemyElite"  },
                new[]{ "DemonVulture","Enemy_04", "EnemyBoss"   },
            };
            int idx = Mathf.Clamp(tier - 1, 0, 3);
            foreach (string hint in tierHints[idx])
            {
                var guids = AssetDatabase.FindAssets($"{hint} t:Prefab");
                if (guids.Length == 0) guids = AssetDatabase.FindAssets($"{hint} t:GameObject");
                if (guids.Length > 0)
                {
                    string path   = AssetDatabase.GUIDToAssetPath(guids[0]);
                    var    prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    if (prefab == null) continue;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
                    go.transform.localPosition = pos;
                    return go;
                }
            }
            return null;
        }

        // â”€â”€ IÅŸÄ±k KaynaklarÄ± â€” Referans: karanlÄ±k gotik + sÄ±cak fener/kampfire â”€
        static void BuildLights(Transform parent)
        {
            var t = new GameObject("_RPG_Lighting").transform;
            t.SetParent(parent);

            // Direktional â€” bulutlu gÃ¶kyÃ¼zÃ¼, soÄŸuk mavi-gri, Ã§ok dÃ¼ÅŸÃ¼k yoÄŸunluk
            var sunGo = new GameObject("_RPG_Sun");
            sunGo.transform.SetParent(t);
            sunGo.transform.localEulerAngles = new Vector3(38f, 195f, 0f); // sol-Ã¼stten
            var sun = sunGo.AddComponent<Light>();
            sun.type           = LightType.Directional;
            sun.color          = new Color(0.58f, 0.64f, 0.78f); // soÄŸuk mavi-gri bulut Ä±ÅŸÄ±ÄŸÄ±
            sun.intensity      = 0.28f;                           // Ã§ok dÃ¼ÅŸÃ¼k â€” gotik karanlÄ±k
            sun.shadows        = LightShadows.Soft;
            sun.shadowStrength = 0.92f;

            // Kampfire â€” sol kulÃ¼be Ã¶nÃ¼nde (sÄ±cak turuncu, referans tÃ¼m gÃ¶rsellerde)
            AddPointLight(t, new Vector3(-5f, 0.8f, 12.5f), new Color(1.0f, 0.38f, 0.05f), 3.8f, 18f);

            // Sol kulÃ¼be fener Ä±ÅŸÄ±ÄŸÄ± (kulÃ¼be Z=18, X=-9, biz global)
            AddPointLight(t, new Vector3(-12f, 2.5f, 15f), new Color(1.0f, 0.60f, 0.25f), 1.6f, 12f);

            // SaÄŸ kulÃ¼be fener direÄŸi (X=+10, Z=22 outpost, global offset)
            AddPointLight(t, new Vector3(7f, 4.5f, 19f), new Color(1.0f, 0.62f, 0.28f), 1.4f, 10f);

            // Kale sihirli Ä±ÅŸÄ±n parlamasÄ± â€” uzakta, soluk mor (Z=85)
            AddPointLight(t, new Vector3(0f, 30f, 85f), new Color(0.72f, 0.48f, 1.0f), 6f, 80f);

            // Kale kapÄ±sÄ± Ã¶nÃ¼ â€” faint blue-purple glow
            AddPointLight(t, new Vector3(0f, 2f, 75f), new Color(0.30f, 0.18f, 0.58f), 1.8f, 25f);
        }

        // â”€â”€ Kamera + Player â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        [MenuItem("Tools/Autopilot/6 - Ensure Camera + Player")]
        public static void EnsureCameraAndPlayer()
        {
            if (Camera.main == null)
            {
                var camGo = new GameObject("Main Camera");
                camGo.tag = "MainCamera";
                // Kamera ROOT seviyesinde â€” NukeSceneObjects tarafÄ±ndan silinmez
                camGo.transform.SetPositionAndRotation(
                    new Vector3(0f, 5f, -14f), Quaternion.Euler(15f, 0f, 0f));
                var cam = camGo.AddComponent<Camera>();
                cam.fieldOfView   = 65f;
                cam.nearClipPlane = 0.2f;
                cam.farClipPlane  = 600f;
                camGo.AddComponent<AudioListener>();
                Undo.RegisterCreatedObjectUndo(camGo, "Add Camera");
            }
            else
            {
                var cam = Camera.main;
                if (cam.transform.parent != null && cam.transform.root.name.StartsWith("_RPG_"))
                    cam.transform.SetParent(null);
            }

            if (GameObject.FindGameObjectWithTag("Player") == null)
            {
                var pg = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                pg.name = "_RPG_Player";
                pg.tag  = "Player";
                pg.transform.position = new Vector3(0f, 1.1f, 0f); // yolun baÅŸÄ±
                ApplyMat(pg, new Color(0.22f, 0.25f, 0.32f));
                pg.AddComponent<CharacterController>();
                var pcType = System.Type.GetType("Gameplay.PlayerController, Assembly-CSharp");
                if (pcType != null) pg.AddComponent(pcType);
                Undo.RegisterCreatedObjectUndo(pg, "Add Player");
            }

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        }

        // â”€â”€ PBR Materyal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static void ApplyPbrGroundMat(GameObject go, string texSet, string subFolder,
                                       float tiling, float smoothness, Color fallback)
        {
            var mr = go.GetComponent<MeshRenderer>();
            if (mr == null) return;

            string basePath  = $"Assets/FantasyRPG/Textures/{subFolder}/{texSet}";
            var    colorTex  = AssetDatabase.LoadAssetAtPath<Texture2D>($"{basePath}_2K-JPG_Color.jpg");
            var    normalTex = AssetDatabase.LoadAssetAtPath<Texture2D>($"{basePath}_2K-JPG_NormalDX.jpg");

            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Sprites/Default");
            if (shader == null) { if (mr.sharedMaterial != null) mr.sharedMaterial.color = fallback; return; }

            var mat = new Material(shader) { name = $"_RPG_Mat_{texSet}" };
            SetColor(mat, colorTex != null ? Color.white : fallback);
            SetFloat(mat, "_Smoothness", smoothness);
            SetFloat(mat, "_Glossiness", smoothness);

            if (colorTex  != null) { SetTex(mat, "_BaseColorMap", colorTex,  tiling); SetTex(mat, "_MainTex",  colorTex,  tiling); }
            if (normalTex != null) { SetTex(mat, "_NormalMap",    normalTex, tiling); SetTex(mat, "_BumpMap",  normalTex, tiling);
                                     SetFloat(mat, "_NormalScale", 1.0f); SetFloat(mat, "_BumpScale", 1.0f); }

            mr.sharedMaterial = mat;
        }

        // â”€â”€ YardÄ±mcÄ±lar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        static float GetPrefabMaxDim(GameObject prefab)
        {
            float max = 0f;
            foreach (var mf in prefab.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null)
                { var s = mf.sharedMesh.bounds.size; max = Mathf.Max(max, s.x, s.y, s.z); }
            foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.sharedMesh != null)
                { var s = smr.sharedMesh.bounds.size; max = Mathf.Max(max, s.x, s.y, s.z); }
            return max;
        }

        static GameObject SpawnGLB(Transform parent, string nameHint,
            Vector3 pos, Vector3 rot, Vector3 scale, float targetMeters = 0f)
        {
            string[] guids = AssetDatabase.FindAssets($"{nameHint} t:GameObject", new[] { "Assets/FantasyRPG" });
            if (guids.Length == 0) guids = AssetDatabase.FindAssets(nameHint, new[] { "Assets/FantasyRPG" });
            if (guids.Length == 0) return null;

            string path   = AssetDatabase.GUIDToAssetPath(guids[0]);
            var    prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) return null;

            Vector3 finalScale = scale;
            if (targetMeters > 0f)
            {
                float natural = GetPrefabMaxDim(prefab);
                finalScale = natural > 0.001f
                    ? Vector3.one * (targetMeters / natural * scale.x)
                    : Vector3.one * (targetMeters * scale.x);
            }

            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.transform.SetLocalPositionAndRotation(pos, Quaternion.Euler(rot));
            go.transform.localScale = finalScale;
            go.name = $"_RPG_{nameHint}";
            return go;
        }

        static void SpawnPrefabByPath(Transform parent, string assetPath,
            Vector3 pos, Vector3 rot, float targetMeters = 0f, float scaleMult = 1f)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (prefab == null) return;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.transform.SetLocalPositionAndRotation(pos, Quaternion.Euler(rot));
            float natural = GetPrefabMaxDim(prefab);
            go.transform.localScale = Vector3.one * (targetMeters > 0f && natural > 0.001f
                ? targetMeters / natural * scaleMult : scaleMult);
            go.name = "_RPG_" + Path.GetFileNameWithoutExtension(assetPath);
        }

        static List<string> FindGLBAssets(string folder, string keyword, int max) =>
            AssetDatabase.FindAssets($"{keyword} t:GameObject", new[] { $"Assets/FantasyRPG/{folder}" })
                .Take(max).Select(AssetDatabase.GUIDToAssetPath).ToList();

        static void AddPointLight(Transform parent, Vector3 pos, Color color, float intensity, float range)
        {
            var go = new GameObject($"_RPG_Light_{pos.x:F0}_{pos.z:F0}");
            go.transform.SetParent(parent);
            go.transform.localPosition = pos;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point; l.color = color;
            l.intensity = intensity;  l.range = range;
            l.shadows = LightShadows.Soft;
        }

        static void ApplyMat(GameObject go, Color color)
        {
            var mr = go.GetComponent<MeshRenderer>();
            if (mr == null) return;
            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Sprites/Default");
            if (shader == null) return;
            var mat = new Material(shader);
            SetColor(mat, color);
            mr.sharedMaterial = mat;
        }

        static void SetColor(Material m, Color c)
        {
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            else if (m.HasProperty("_Color")) m.SetColor("_Color", c);
        }

        static void SetFloat(Material m, string prop, float v)
        { if (m.HasProperty(prop)) m.SetFloat(prop, v); }

        static void SetTex(Material m, string prop, Texture2D tex, float tiling)
        {
            if (!m.HasProperty(prop)) return;
            m.SetTexture(prop, tex);
            m.SetTextureScale(prop, new Vector2(tiling, tiling));
        }

        // â”€â”€ Menu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        [MenuItem("Tools/Autopilot/3 - Full Setup (Import + Scene + Materials)")]
        public static void FullSetup()
        {
            ImportAssets();
            EditorApplication.delayCall += () =>
            {
                BuildScene();
                EditorApplication.delayCall += SceneMaterialPainter.PaintAll;
            };
        }

        [MenuItem("Tools/Autopilot/4 - Clear Autopilot Task Cache")]
        public static void ClearTaskCache()
        {
            string[] paths = {
                "AutopilotData/tasks.json",
                Path.Combine(Application.dataPath, "..", "AutopilotData", "tasks.json")
            };
            foreach (var p in paths)
                if (File.Exists(p)) { File.Delete(p); Debug.Log($"[SceneBuilder] Silindi: {p}"); }
        }

        // AutopilotBrain iÃ§in public entry â€” tÃ¼m sahneyi temizle + yeniden kur
        public static void ClearAndRebuild() => BuildScene();
    }
}
#endif


