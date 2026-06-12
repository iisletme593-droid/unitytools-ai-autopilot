#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // Referans gorsel palet: yesil cimen, krem kale tasi, misty mavi-gri sis, sabah isigi.
    // Her Renderer'in her alt materyalini (sharedMaterials[]) tek tek kontrol eder.
    // Oncelik sirasi: (1) materyal ismi → (2) obje ismi → (3) skip.
    // Dokulu GLB materyalleri EZILMEZ; sadece doku/renk atanmamis materyaller boyanir.
    public static class SceneMaterialPainter
    {
        // ── Materyal tanimi ──────────────────────────────────────────────────
        private struct MatDef
        {
            public Color albedo;
            public float metallic;
            public float smoothness;
            public Color emissive;
            public bool  doubleSided;

            public MatDef(float r, float g, float b,
                          float m = 0f, float s = 0.25f,
                          float er = 0f, float eg = 0f, float eb = 0f,
                          bool ds = false)
            {
                albedo     = new Color(r, g, b, 1f);
                metallic   = m;
                smoothness = s;
                emissive   = new Color(er, eg, eb);
                doubleSided = ds;
            }
        }

        // ── MATERYAL ISMI → RENK haritasi (en hassas esleme) ─────────────────
        // Unity'nin linear color space'inde degerler.
        // Yaprak: linear 0.04/0.17/0.03 → ekranda koyu orman yesili gorunur.
        static readonly (string kw, MatDef def)[] ByMaterialName =
        {
            // ── YAPRAK / AGAC YESILI ──────────────────────────────────────────
            ("leaf",      new MatDef(0.025f,0.14f,0.015f, s:0.06f, ds:true)),
            ("leaves",    new MatDef(0.025f,0.14f,0.015f, s:0.06f, ds:true)),
            ("foliage",   new MatDef(0.030f,0.16f,0.018f, s:0.07f, ds:true)),
            ("pine",      new MatDef(0.020f,0.12f,0.012f, s:0.05f, ds:true)),
            ("fir",       new MatDef(0.018f,0.11f,0.010f, s:0.04f, ds:true)),
            ("needle",    new MatDef(0.022f,0.13f,0.013f, s:0.05f, ds:true)),
            ("frond",     new MatDef(0.028f,0.15f,0.016f, s:0.07f, ds:true)),
            ("canopy",    new MatDef(0.022f,0.13f,0.012f, s:0.05f, ds:true)),
            ("branch",    new MatDef(0.14f, 0.09f,0.055f, s:0.11f)),         // dal → kahverengi
            ("twig",      new MatDef(0.13f, 0.08f,0.050f, s:0.10f)),
            // ── KABUK / GOVDE ─────────────────────────────────────────────────
            ("bark",      new MatDef(0.13f, 0.085f,0.050f, s:0.12f)),
            ("trunk",     new MatDef(0.12f, 0.080f,0.048f, s:0.10f)),
            ("log",       new MatDef(0.15f, 0.095f,0.055f, s:0.12f)),
            ("stump",     new MatDef(0.15f, 0.095f,0.058f, s:0.11f)),
            ("wood",      new MatDef(0.18f, 0.115f,0.070f, s:0.15f)),
            ("plank",     new MatDef(0.20f, 0.130f,0.080f, s:0.12f)),
            ("timber",    new MatDef(0.19f, 0.120f,0.075f, s:0.13f)),
            // ── KAYA / TAS ────────────────────────────────────────────────────
            ("rock",      new MatDef(0.20f, 0.19f,0.17f,  s:0.20f)),
            ("stone",     new MatDef(0.21f, 0.20f,0.18f,  s:0.22f)),
            ("boulder",   new MatDef(0.18f, 0.17f,0.15f,  s:0.18f)),
            ("granite",   new MatDef(0.23f, 0.21f,0.19f,  s:0.25f)),
            ("cliff",     new MatDef(0.19f, 0.18f,0.16f,  s:0.18f)),
            ("gravel",    new MatDef(0.22f, 0.20f,0.18f,  s:0.15f)),
            ("cobble",    new MatDef(0.24f, 0.22f,0.20f,  s:0.28f)),
            // ── YOSUN / BITKI ─────────────────────────────────────────────────
            ("moss",      new MatDef(0.06f, 0.14f,0.04f,  s:0.08f)),
            ("lichen",    new MatDef(0.08f, 0.15f,0.06f,  s:0.07f)),
            ("grass",     new MatDef(0.025f,0.065f,0.015f, s:0.06f)),  // referans: koyu gri-yesil (gotik)
            ("fern",      new MatDef(0.06f, 0.19f,0.04f,  s:0.07f)),
            // ── METAL ─────────────────────────────────────────────────────────
            ("iron",      new MatDef(0.35f, 0.33f,0.31f,  m:0.85f,s:0.50f)),
            ("steel",     new MatDef(0.40f, 0.38f,0.36f,  m:0.88f,s:0.65f)),
            ("bronze",    new MatDef(0.50f, 0.36f,0.18f,  m:0.75f,s:0.55f)),
            ("gold",      new MatDef(0.68f, 0.52f,0.14f,  m:0.92f,s:0.78f)),
            ("brass",     new MatDef(0.52f, 0.38f,0.18f,  m:0.75f,s:0.58f)),
            ("silver",    new MatDef(0.55f, 0.55f,0.54f,  m:0.90f,s:0.80f)),
            ("copper",    new MatDef(0.50f, 0.28f,0.14f,  m:0.80f,s:0.60f)),
            ("rust",      new MatDef(0.35f, 0.18f,0.06f,  m:0.40f,s:0.20f)),
            ("blade",     new MatDef(0.45f, 0.43f,0.40f,  m:0.90f,s:0.72f)),
            ("edge",      new MatDef(0.48f, 0.46f,0.44f,  m:0.92f,s:0.78f)),
            ("handle",    new MatDef(0.20f, 0.13f,0.08f,  s:0.18f)),         // ahsap sap
            ("hilt",      new MatDef(0.45f, 0.35f,0.18f,  m:0.80f,s:0.62f)),
            ("guard",     new MatDef(0.38f, 0.36f,0.34f,  m:0.82f,s:0.55f)),
            ("pommel",    new MatDef(0.42f, 0.32f,0.16f,  m:0.85f,s:0.65f)),
            ("tsuba",     new MatDef(0.35f, 0.28f,0.14f,  m:0.80f,s:0.60f)),
            ("grip",      new MatDef(0.15f, 0.10f,0.07f,  s:0.15f)),
            // ── KUMAS / DERI ──────────────────────────────────────────────────
            ("cloth",     new MatDef(0.18f, 0.16f,0.14f,  s:0.07f)),
            ("fabric",    new MatDef(0.16f, 0.14f,0.12f,  s:0.06f)),
            ("leather",   new MatDef(0.20f, 0.12f,0.07f,  s:0.18f)),
            ("fur",       new MatDef(0.22f, 0.17f,0.12f,  s:0.05f)),
            ("silk",      new MatDef(0.25f, 0.22f,0.18f,  s:0.45f)),
            ("robe",      new MatDef(0.12f, 0.08f,0.18f,  s:0.08f)),         // mor cuce kiyafeti
            // ── KEMIK / KAFATAS ───────────────────────────────────────────────
            ("bone",      new MatDef(0.60f, 0.55f,0.45f,  s:0.22f)),
            ("skull",     new MatDef(0.58f, 0.53f,0.43f,  s:0.20f)),
            // ── TUHAF / MAGIK ─────────────────────────────────────────────────
            ("crystal",   new MatDef(0.30f, 0.50f,0.75f,  m:0.0f, s:0.92f, er:0.05f,eg:0.15f,eb:0.35f)),
            ("gem",       new MatDef(0.25f, 0.45f,0.70f,  m:0.0f, s:0.95f, er:0.04f,eg:0.12f,eb:0.30f)),
            ("glass",     new MatDef(0.50f, 0.70f,0.85f,  m:0.0f, s:0.95f)),
            ("orb",       new MatDef(0.20f, 0.35f,0.65f,  m:0.0f, s:0.90f, er:0.08f,eg:0.18f,eb:0.45f)),
            ("scroll",    new MatDef(0.65f, 0.55f,0.38f,  s:0.18f)),
            ("parchment", new MatDef(0.62f, 0.52f,0.35f,  s:0.12f)),
            // ── ATES / ISIK ───────────────────────────────────────────────────
            ("fire",      new MatDef(0.50f, 0.18f,0.02f,  s:0.08f, er:1.8f,eg:0.50f,eb:0.02f)),
            ("flame",     new MatDef(0.55f, 0.20f,0.02f,  s:0.05f, er:2.0f,eg:0.55f,eb:0.02f)),
            ("ember",     new MatDef(0.40f, 0.12f,0.01f,  s:0.05f, er:1.2f,eg:0.25f,eb:0.01f)),
            ("glow",      new MatDef(0.60f, 0.45f,0.20f,  m:0.2f, s:0.50f, er:0.6f,eg:0.35f,eb:0.05f)),
            // ── TOPRAK / ZEMIN ────────────────────────────────────────────────
            ("dirt",      new MatDef(0.14f, 0.10f,0.07f,  s:0.10f)),   // patika toprak
            ("soil",      new MatDef(0.12f, 0.09f,0.065f, s:0.08f)),
            ("mud",       new MatDef(0.13f, 0.10f,0.072f, s:0.15f)),
            ("ground",    new MatDef(0.025f,0.065f,0.015f, s:0.06f)),  // referans: koyu gotik zemin
            ("terrain",   new MatDef(0.025f,0.060f,0.014f,s:0.06f)),  // referans: koyu zemin
        };

        // ── OBJE ISMI → RENK (ikincil esleme) ────────────────────────────────
        static readonly (string kw, MatDef def)[] ByObjectName =
        {
            // Zemin — referans: koyu gri-yesil (gotik atmosfer, yoğun sis)
            ("OuterGround",  new MatDef(0.025f,0.065f,0.015f, s:0.06f)), // koyu gri-yesil
            ("GrassGround",  new MatDef(0.025f,0.065f,0.015f, s:0.06f)), // koyu gri-yesil
            ("DirtPath",     new MatDef(0.08f, 0.062f,0.040f, s:0.14f)), // koyu camurlu toprak
            ("CourtStone",   new MatDef(0.12f, 0.110f,0.095f, s:0.28f)), // koyu kale avlusu
            ("CourtGround",  new MatDef(0.10f, 0.090f,0.075f, s:0.22f)), // koyu avlu zemini
            ("DungeonFloor", new MatDef(0.06f, 0.050f,0.040f, s:0.38f)), // koyu zindan zemini
            // Kale — referans: koyu gotik tas, siyah kuleler (816ea051 / 0f1450a9)
            ("Wall",         new MatDef(0.09f, 0.080f,0.070f, s:0.14f)), // siyah kale duvari
            ("Tower",        new MatDef(0.08f, 0.070f,0.060f, s:0.12f)), // siyah kule
            ("TowerTop",     new MatDef(0.05f, 0.040f,0.060f, s:0.10f)), // koyu mor-siyah spire
            ("CastleGate",   new MatDef(0.06f, 0.050f,0.040f, m:0.15f,s:0.25f)), // demir kapi
            // Agac (GLB bulunamazsa capsule gibi fallback)
            ("PineTree",     new MatDef(0.025f,0.14f,0.015f, s:0.06f)),
            ("FirTree",      new MatDef(0.020f,0.12f,0.012f, s:0.05f)),
            ("IslandTree",   new MatDef(0.10f, 0.27f,0.050f, s:0.10f, ds:true)), // arborikültür: orta kanopi
            ("DeadTreeTrunk",new MatDef(0.16f,0.10f,0.060f,  s:0.10f)),
            ("TreeStump",    new MatDef(0.15f,0.095f,0.055f, s:0.11f)),
            // Kaya
            ("Boulder",      new MatDef(0.18f,0.17f,0.15f,  s:0.18f)),
            ("RockFace",     new MatDef(0.17f,0.16f,0.14f,  s:0.16f)),
            ("Rock",         new MatDef(0.20f,0.19f,0.17f,  s:0.20f)),
            // Mobilya
            ("Bed",          new MatDef(0.17f,0.10f,0.065f, s:0.12f)),
            ("Table",        new MatDef(0.19f,0.12f,0.075f, s:0.16f)),
            ("Cabinet",      new MatDef(0.16f,0.10f,0.062f, s:0.13f)),
            ("Bookshelf",    new MatDef(0.17f,0.11f,0.068f, s:0.12f)),
            ("Chair",        new MatDef(0.18f,0.11f,0.070f, s:0.14f)),
            ("Stool",        new MatDef(0.19f,0.12f,0.075f, s:0.12f)),
            ("Console",      new MatDef(0.17f,0.11f,0.068f, s:0.14f)),
            // Depolama
            ("Chest",        new MatDef(0.20f,0.14f,0.085f, m:0.12f,s:0.28f)),
            ("Crate",        new MatDef(0.20f,0.13f,0.082f, s:0.11f)),
            ("Barrel",       new MatDef(0.17f,0.11f,0.065f, s:0.16f)),
            ("Basket",       new MatDef(0.22f,0.16f,0.092f, s:0.09f)),
            // Isik / ates
            ("Lantern",      new MatDef(0.48f,0.36f,0.16f,  m:0.60f,s:0.55f, er:0.5f,eg:0.18f,eb:0f)),
            ("Candlestick",  new MatDef(0.48f,0.36f,0.16f,  m:0.70f,s:0.60f)),
            ("StoneFire",    new MatDef(0.20f,0.14f,0.09f,  s:0.18f, er:0.8f,eg:0.22f,eb:0f)),
            // Dekor
            ("Bust",         new MatDef(0.50f,0.48f,0.45f,  s:0.40f)),
            ("Statue",       new MatDef(0.30f,0.28f,0.26f,  s:0.28f)),
            ("Vase",         new MatDef(0.48f,0.36f,0.18f,  m:0.70f,s:0.60f)),
            ("Mirror",       new MatDef(0.52f,0.50f,0.46f,  m:0.80f,s:0.85f)),
            ("PocketWatch",  new MatDef(0.58f,0.43f,0.18f,  m:0.90f,s:0.80f)),
        };

        // ── Ana boyama fonksiyonu ────────────────────────────────────────────
        [MenuItem("Tools/Autopilot/5 - Paint Scene Materials (Reference Palette)")]
        public static void PaintAll()
        {
            int painted = 0;
            int skipped = 0;

            var renderers = Object.FindObjectsByType<MeshRenderer>(
                FindObjectsInactive.Include);

            foreach (var mr in renderers)
            {
                if (mr == null) continue;
                if (!IsUnderRPGRoot(mr.transform)) continue;

                var mats = mr.sharedMaterials;
                bool changed = false;

                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) { continue; }

                    // Dokulu / duzgun import edilmis → dokunma
                    if (HasRealTexture(mats[i])) { skipped++; continue; }
                    // Zaten bizim materyalimiz → dokunma
                    if (mats[i].name.StartsWith("_RPG_Mat_")) { skipped++; continue; }

                    // Esleme: once materyal ismine, sonra obje ismine bak
                    MatDef? match = FindByMatName(mats[i].name)
                                 ?? FindByObjName(mr.gameObject.name);

                    if (match == null) { skipped++; continue; }

                    mats[i] = BuildMaterial(match.Value, $"_RPG_Mat_{mr.gameObject.name}_{i}");
                    changed = true;
                    painted++;
                }

                if (changed) mr.sharedMaterials = mats;
            }

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();

            string msg = $"{painted} materyal boyandi, {skipped} atlandi (doku/mevcut). Palet: yesil cimen + krem kale.";
            Debug.Log($"[MaterialPainter] {msg}");
            EditorUtility.DisplayDialog("Materyal Boyama Tamam", msg + "\nSahne kaydedildi.", "OK");
        }

        // ── Yardimci: _RPG_ altinda mi? ──────────────────────────────────────
        static bool IsUnderRPGRoot(Transform t)
        {
            while (t != null)
            {
                if (t.name.StartsWith("_RPG_") || t.name.StartsWith("TI_Moody")) return true;
                t = t.parent;
            }
            return false;
        }

        // ── Dokulu materyal kontrolu ─────────────────────────────────────────
        // glTFast'in dogru import ettigi materyaller _BaseColorMap veya _MainTex
        // iceriyor ya da materyal GLB asset icinde gomiluyor.
        static bool HasRealTexture(Material mat)
        {
            // Texture kontrolu
            if (mat.HasProperty("_BaseColorMap") && mat.GetTexture("_BaseColorMap") != null) return true;
            if (mat.HasProperty("_MainTex")      && mat.GetTexture("_MainTex")      != null) return true;

            // Materyal bir GLB/FBX/OBJ icinde gomulu mu? (import yolu biter .glb vs)
            string path = AssetDatabase.GetAssetPath(mat);
            if (!string.IsNullOrEmpty(path))
            {
                string ext = System.IO.Path.GetExtension(path).ToLower();
                if (ext == ".glb" || ext == ".gltf" || ext == ".fbx" || ext == ".obj")
                    return true;
            }

            // _BaseColor'u beyaz/gri olan varsayilan Unity materyali mi?
            // Kendi rengi varsa (eklenebilir renk != beyaz) koru
            if (mat.HasProperty("_BaseColor"))
            {
                Color bc = mat.GetColor("_BaseColor");
                // Belirgin bir renk atanmissa (varsayilan gri degil) koru
                float diff = Mathf.Abs(bc.r - bc.g) + Mathf.Abs(bc.g - bc.b);
                if (diff > 0.08f && (bc.r + bc.g + bc.b) < 2.7f) return true;
            }

            return false;
        }

        // ── Materyal ismiyle esleme ───────────────────────────────────────────
        static MatDef? FindByMatName(string matName)
        {
            string lower = matName.ToLower();
            foreach (var (kw, def) in ByMaterialName)
                if (lower.Contains(kw)) return def;
            return null;
        }

        // ── Obje ismiyle esleme ───────────────────────────────────────────────
        static MatDef? FindByObjName(string objName)
        {
            string lower = objName.ToLower();
            foreach (var (kw, def) in ByObjectName)
                if (lower.Contains(kw.ToLower())) return def;
            return null;
        }

        // ── HDRP/Lit materyal olustur ─────────────────────────────────────────
        static Material BuildMaterial(MatDef def, string name)
        {
            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard");
            var mat = new Material(shader) { name = name };

            SetColor(mat, "_BaseColor", def.albedo);
            SetColor(mat, "_Color",     def.albedo);   // Standard fallback
            SetFloat(mat, "_Metallic",   def.metallic);
            SetFloat(mat, "_Smoothness", def.smoothness);
            SetFloat(mat, "_Glossiness", def.smoothness);

            if (def.emissive.maxColorComponent > 0.02f)
            {
                Color emBoost = def.emissive * 3f;
                SetColor(mat, "_EmissiveColor", emBoost);
                SetColor(mat, "_EmissionColor", emBoost);
                SetFloat(mat, "_EmissiveIntensity", 3f);
                mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }

            if (def.doubleSided)
            {
                // Yapraklar icin cift tarafli render (HDRP)
                SetFloat(mat, "_DoubleSidedEnable",    1f);
                SetFloat(mat, "_DoubleSidedNormalMode", 1f);
                mat.EnableKeyword("_DOUBLESIDED_ON");
            }

            return mat;
        }

        static void SetColor(Material m, string prop, Color v)
        { if (m.HasProperty(prop)) m.SetColor(prop, v); }

        static void SetFloat(Material m, string prop, float v)
        { if (m.HasProperty(prop)) m.SetFloat(prop, v); }

        // ── Autopilot task entry ──────────────────────────────────────────────
        public static bool RunAsTask(out string reason)
        {
            try { PaintAll(); reason = "Referans palet materyal boyama tamam (yesil cimen + krem kale)."; return true; }
            catch (System.Exception ex) { reason = $"MaterialPainter hata: {ex.Message}"; return false; }
        }
    }
}
#endif

