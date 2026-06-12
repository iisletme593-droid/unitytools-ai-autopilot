#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // Nature_Trees_06_IslandTree için arborikültür tekniğine göre materyal boyama.
    //
    // Broadleaf deciduous palet (linear color space):
    //   Kanopi / yaprak    → foliage anahtar kelimesiyle tespit
    //   Kabuk / gövde      → bark anahtar kelimesiyle tespit
    //   Bilinmiyor         → yükseklik bazlı sezgisel (üst=yaprak, alt=kabuk)
    //
    // GLB embedded materyaller dahil: HasRealTexture kontrolü bypass edilir.
    // Çalıştır: Tools > Autopilot > Paint IslandTree (Arboriculture)
    public static class IslandTreePainter
    {
        // ── Arborikültür renk paleti (linear) ────────────────────────────────
        // Broadleaf deciduous, ılıman iklim, yaz yaprağı.
        // Katman prensibi: güneş → orta → gölge (chlorophyll a/b oranı değişimi).

        // Yaprak — güneş kanopisi: dışa bakan, chlorophyll a + carotenoid, açık sarı-yeşil
        static readonly Color LeafSun   = new Color(0.14f, 0.36f, 0.07f);  // sRGB ≈(0.40, 0.64, 0.28)
        // Yaprak — orta kanopi: dominant chlorophyll, standard yaz yeşili
        static readonly Color LeafMid   = new Color(0.10f, 0.27f, 0.05f);  // sRGB ≈(0.34, 0.55, 0.24)
        // Yaprak — iç/gölge: shade-adapted, mavi-yeşil tonları
        static readonly Color LeafShade = new Color(0.06f, 0.17f, 0.04f);  // sRGB ≈(0.26, 0.44, 0.21)
        // Kabuk — üst dal: smooth, açık gri-kahve
        static readonly Color BarkUpper = new Color(0.15f, 0.105f,0.065f); // sRGB ≈(0.41, 0.34, 0.27)
        // Kabuk — gövde orta: typical deciduous bark
        static readonly Color BarkMid   = new Color(0.11f, 0.075f,0.045f); // sRGB ≈(0.35, 0.29, 0.23)
        // Kabuk — taban/kök: eski, koyu, nemli
        static readonly Color BarkBase  = new Color(0.08f, 0.052f,0.030f); // sRGB ≈(0.30, 0.24, 0.19)

        // ── Anahtar kelime listeleri ──────────────────────────────────────────
        static readonly string[] FoliageKws = {
            "leaf", "leaves", "foliage", "canopy", "frond", "crown",
            "needle", "pine", "fir", "green", "flora", "branch_end"
        };
        static readonly string[] BarkKws = {
            "bark", "trunk", "wood", "branch", "twig", "log",
            "stump", "root", "stem", "base", "timber"
        };

        // ── Ana giriş noktası ─────────────────────────────────────────────────
        [MenuItem("Tools/Autopilot/Paint IslandTree (Arboriculture)")]
        public static void PaintAll()
        {
            var allGo = Object.FindObjectsByType<GameObject>(
                FindObjectsInactive.Include);

            var treeRoots = new HashSet<GameObject>();
            foreach (var go in allGo)
            {
                if (go == null) continue;
                if (go.name.Contains("IslandTree", System.StringComparison.OrdinalIgnoreCase))
                    treeRoots.Add(go.transform.root.gameObject);
            }

            if (treeRoots.Count == 0)
            {
                Debug.LogWarning("[IslandTreePainter] Sahnede IslandTree nesnesi yok.");
                EditorUtility.DisplayDialog("IslandTree Boyama",
                    "Sahnede IslandTree nesnesi bulunamadı.\nÖnce sahneyi oluşturun.", "OK");
                return;
            }

            int painted = 0;

            foreach (var root in treeRoots)
            {
                var renderers = root.GetComponentsInChildren<MeshRenderer>(includeInactive: true);
                foreach (var mr in renderers)
                {
                    if (mr == null) continue;
                    painted += PaintRenderer(mr);
                }
            }

            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();

            string msg = $"{treeRoots.Count} IslandTree → {painted} materyal arborikültür paleti ile boyandı.";
            Debug.Log($"[IslandTreePainter] {msg}");
            EditorUtility.DisplayDialog("IslandTree Arborikültür Boyama Tamam", msg + "\nSahne kaydedildi.", "OK");
        }

        // ── Tek renderer boyama ───────────────────────────────────────────────
        static int PaintRenderer(MeshRenderer mr)
        {
            var mats = mr.sharedMaterials;
            bool changed = false;
            int count = 0;

            // Bu renderer'ın bounding box yüksekliğini kabuk/yaprak tahmini için kullan
            float worldTop    = mr.bounds.max.y;
            float worldBottom = mr.bounds.min.y;
            float height      = worldTop - worldBottom;

            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null) continue;
                if (mats[i].name.StartsWith("_RPG_IT_")) continue; // Zaten boyalı

                PartType part = DetectPart(mats[i].name, mr.gameObject.name);

                // Anahtar kelime eşleşmesi yoksa → yükseklik sezgisi
                if (part == PartType.Unknown)
                    part = height > 1.5f ? PartType.Foliage : PartType.Bark;

                mats[i] = BuildMat(part, mr.gameObject.name, i);
                changed = true;
                count++;
            }

            if (changed) mr.sharedMaterials = mats;
            return count;
        }

        // ── Parça tipi tespiti ────────────────────────────────────────────────
        enum PartType { Unknown, Foliage, Bark }

        static PartType DetectPart(string matName, string objName)
        {
            string lower = (matName + " " + objName).ToLower();
            foreach (var kw in FoliageKws)
                if (lower.Contains(kw)) return PartType.Foliage;
            foreach (var kw in BarkKws)
                if (lower.Contains(kw)) return PartType.Bark;
            // "Material", "default", "mat_0" gibi isimler → yaprak fallback (görsel katkısı daha fazla)
            if (lower.StartsWith("mat") || lower.Contains("default") || lower.Contains("material"))
                return PartType.Foliage;
            return PartType.Unknown;
        }

        // ── Materyal üretici ─────────────────────────────────────────────────
        // Arborikültür katmanları:
        //   Foliage → LeafMid albedo, double-sided, subsurface translucency, matte
        //   Bark    → BarkMid albedo, single-sided, slightly wet smoothness
        static Material BuildMat(PartType part, string objName, int slot)
        {
            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard");
            string mName = $"_RPG_IT_{part}_{objName}_{slot}";
            var mat = new Material(shader) { name = mName };

            if (part == PartType.Foliage)
            {
                // Orta kanopi yeşili — hem güneş hem gölge ortası
                SetColor(mat, "_BaseColor", LeafMid);
                SetColor(mat, "_Color",     LeafMid);
                SetFloat(mat, "_Metallic",   0f);
                SetFloat(mat, "_Smoothness", 0.10f);   // mat yaprak (wax yüzeyi düşük)
                SetFloat(mat, "_Glossiness", 0.10f);

                // HDRP çift taraflı render (yaprak alt yüzü görünür)
                SetFloat(mat, "_DoubleSidedEnable",     1f);
                SetFloat(mat, "_DoubleSidedNormalMode", 1f);
                mat.EnableKeyword("_DOUBLESIDED_ON");

                // Subsurface scattering: yaprak translucency etkisi
                // Güneş ışığı yapraktan geçerken alt yüz aydınlanır → yeşil-sarı glow
                SetFloat(mat, "_SubsurfaceMask", 0.22f);
                SetFloat(mat, "_Thickness",      0.55f);

                // Hafif emisyon: iç ışık geçirgenliği (kloroplast parlaması)
                Color leafGlow = new Color(0.006f, 0.018f, 0.003f);
                SetColor(mat, "_EmissiveColor", leafGlow);
                mat.EnableKeyword("_EMISSION");
            }
            else // Bark
            {
                SetColor(mat, "_BaseColor", BarkMid);
                SetColor(mat, "_Color",     BarkMid);
                SetFloat(mat, "_Metallic",   0f);
                SetFloat(mat, "_Smoothness", 0.22f);   // hafif nemli kabuk yüzeyi
                SetFloat(mat, "_Glossiness", 0.22f);
                SetFloat(mat, "_SubsurfaceMask", 0f);
            }

            return mat;
        }

        static void SetColor(Material m, string p, Color v) { if (m.HasProperty(p)) m.SetColor(p, v); }
        static void SetFloat(Material m, string p, float v) { if (m.HasProperty(p)) m.SetFloat(p, v); }

        // ── Autopilot task entry ──────────────────────────────────────────────
        public static bool RunAsTask(out string reason)
        {
            try { PaintAll(); reason = "IslandTree arborikültür boyama tamam."; return true; }
            catch (System.Exception ex) { reason = $"IslandTreePainter hata: {ex.Message}"; return false; }
        }
    }
}
#endif

