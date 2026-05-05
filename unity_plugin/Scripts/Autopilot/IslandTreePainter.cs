#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // Nature_Trees_06_IslandTree iÃ§in arborikÃ¼ltÃ¼r tekniÄŸine gÃ¶re materyal boyama.
    //
    // Broadleaf deciduous palet (linear color space):
    //   Kanopi / yaprak    â†’ foliage anahtar kelimesiyle tespit
    //   Kabuk / gÃ¶vde      â†’ bark anahtar kelimesiyle tespit
    //   Bilinmiyor         â†’ yÃ¼kseklik bazlÄ± sezgisel (Ã¼st=yaprak, alt=kabuk)
    //
    // GLB embedded materyaller dahil: HasRealTexture kontrolÃ¼ bypass edilir.
    // Ã‡alÄ±ÅŸtÄ±r: Tools > Autopilot > Paint IslandTree (Arboriculture)
    public static class IslandTreePainter
    {
        // â”€â”€ ArborikÃ¼ltÃ¼r renk paleti (linear) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // Broadleaf deciduous, Ä±lÄ±man iklim, yaz yapraÄŸÄ±.
        // Katman prensibi: gÃ¼neÅŸ â†’ orta â†’ gÃ¶lge (chlorophyll a/b oranÄ± deÄŸiÅŸimi).

        // Yaprak â€” gÃ¼neÅŸ kanopisi: dÄ±ÅŸa bakan, chlorophyll a + carotenoid, aÃ§Ä±k sarÄ±-yeÅŸil
        static readonly Color LeafSun   = new Color(0.14f, 0.36f, 0.07f);  // sRGB â‰ˆ(0.40, 0.64, 0.28)
        // Yaprak â€” orta kanopi: dominant chlorophyll, standard yaz yeÅŸili
        static readonly Color LeafMid   = new Color(0.10f, 0.27f, 0.05f);  // sRGB â‰ˆ(0.34, 0.55, 0.24)
        // Yaprak â€” iÃ§/gÃ¶lge: shade-adapted, mavi-yeÅŸil tonlarÄ±
        static readonly Color LeafShade = new Color(0.06f, 0.17f, 0.04f);  // sRGB â‰ˆ(0.26, 0.44, 0.21)
        // Kabuk â€” Ã¼st dal: smooth, aÃ§Ä±k gri-kahve
        static readonly Color BarkUpper = new Color(0.15f, 0.105f,0.065f); // sRGB â‰ˆ(0.41, 0.34, 0.27)
        // Kabuk â€” gÃ¶vde orta: typical deciduous bark
        static readonly Color BarkMid   = new Color(0.11f, 0.075f,0.045f); // sRGB â‰ˆ(0.35, 0.29, 0.23)
        // Kabuk â€” taban/kÃ¶k: eski, koyu, nemli
        static readonly Color BarkBase  = new Color(0.08f, 0.052f,0.030f); // sRGB â‰ˆ(0.30, 0.24, 0.19)

        // â”€â”€ Anahtar kelime listeleri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static readonly string[] FoliageKws = {
            "leaf", "leaves", "foliage", "canopy", "frond", "crown",
            "needle", "pine", "fir", "green", "flora", "branch_end"
        };
        static readonly string[] BarkKws = {
            "bark", "trunk", "wood", "branch", "twig", "log",
            "stump", "root", "stem", "base", "timber"
        };

        // â”€â”€ Ana giriÅŸ noktasÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                    "Sahnede IslandTree nesnesi bulunamadÄ±.\nÃ–nce sahneyi oluÅŸturun.", "OK");
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

            string msg = $"{treeRoots.Count} IslandTree â†’ {painted} materyal arborikÃ¼ltÃ¼r paleti ile boyandÄ±.";
            Debug.Log($"[IslandTreePainter] {msg}");
            EditorUtility.DisplayDialog("IslandTree ArborikÃ¼ltÃ¼r Boyama Tamam", msg + "\nSahne kaydedildi.", "OK");
        }

        // â”€â”€ Tek renderer boyama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        static int PaintRenderer(MeshRenderer mr)
        {
            var mats = mr.sharedMaterials;
            bool changed = false;
            int count = 0;

            // Bu renderer'Ä±n bounding box yÃ¼ksekliÄŸini kabuk/yaprak tahmini iÃ§in kullan
            float worldTop    = mr.bounds.max.y;
            float worldBottom = mr.bounds.min.y;
            float height      = worldTop - worldBottom;

            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null) continue;
                if (mats[i].name.StartsWith("_RPG_IT_")) continue; // Zaten boyalÄ±

                PartType part = DetectPart(mats[i].name, mr.gameObject.name);

                // Anahtar kelime eÅŸleÅŸmesi yoksa â†’ yÃ¼kseklik sezgisi
                if (part == PartType.Unknown)
                    part = height > 1.5f ? PartType.Foliage : PartType.Bark;

                mats[i] = BuildMat(part, mr.gameObject.name, i);
                changed = true;
                count++;
            }

            if (changed) mr.sharedMaterials = mats;
            return count;
        }

        // â”€â”€ ParÃ§a tipi tespiti â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        enum PartType { Unknown, Foliage, Bark }

        static PartType DetectPart(string matName, string objName)
        {
            string lower = (matName + " " + objName).ToLower();
            foreach (var kw in FoliageKws)
                if (lower.Contains(kw)) return PartType.Foliage;
            foreach (var kw in BarkKws)
                if (lower.Contains(kw)) return PartType.Bark;
            // "Material", "default", "mat_0" gibi isimler â†’ yaprak fallback (gÃ¶rsel katkÄ±sÄ± daha fazla)
            if (lower.StartsWith("mat") || lower.Contains("default") || lower.Contains("material"))
                return PartType.Foliage;
            return PartType.Unknown;
        }

        // â”€â”€ Materyal Ã¼retici â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // ArborikÃ¼ltÃ¼r katmanlarÄ±:
        //   Foliage â†’ LeafMid albedo, double-sided, subsurface translucency, matte
        //   Bark    â†’ BarkMid albedo, single-sided, slightly wet smoothness
        static Material BuildMat(PartType part, string objName, int slot)
        {
            var shader = Shader.Find("HDRP/Lit") ?? Shader.Find("Standard");
            string mName = $"_RPG_IT_{part}_{objName}_{slot}";
            var mat = new Material(shader) { name = mName };

            if (part == PartType.Foliage)
            {
                // Orta kanopi yeÅŸili â€” hem gÃ¼neÅŸ hem gÃ¶lge ortasÄ±
                SetColor(mat, "_BaseColor", LeafMid);
                SetColor(mat, "_Color",     LeafMid);
                SetFloat(mat, "_Metallic",   0f);
                SetFloat(mat, "_Smoothness", 0.10f);   // mat yaprak (wax yÃ¼zeyi dÃ¼ÅŸÃ¼k)
                SetFloat(mat, "_Glossiness", 0.10f);

                // HDRP Ã§ift taraflÄ± render (yaprak alt yÃ¼zÃ¼ gÃ¶rÃ¼nÃ¼r)
                SetFloat(mat, "_DoubleSidedEnable",     1f);
                SetFloat(mat, "_DoubleSidedNormalMode", 1f);
                mat.EnableKeyword("_DOUBLESIDED_ON");

                // Subsurface scattering: yaprak translucency etkisi
                // GÃ¼neÅŸ Ä±ÅŸÄ±ÄŸÄ± yapraktan geÃ§erken alt yÃ¼z aydÄ±nlanÄ±r â†’ yeÅŸil-sarÄ± glow
                SetFloat(mat, "_SubsurfaceMask", 0.22f);
                SetFloat(mat, "_Thickness",      0.55f);

                // Hafif emisyon: iÃ§ Ä±ÅŸÄ±k geÃ§irgenliÄŸi (kloroplast parlamasÄ±)
                Color leafGlow = new Color(0.006f, 0.018f, 0.003f);
                SetColor(mat, "_EmissiveColor", leafGlow);
                mat.EnableKeyword("_EMISSION");
            }
            else // Bark
            {
                SetColor(mat, "_BaseColor", BarkMid);
                SetColor(mat, "_Color",     BarkMid);
                SetFloat(mat, "_Metallic",   0f);
                SetFloat(mat, "_Smoothness", 0.22f);   // hafif nemli kabuk yÃ¼zeyi
                SetFloat(mat, "_Glossiness", 0.22f);
                SetFloat(mat, "_SubsurfaceMask", 0f);
            }

            return mat;
        }

        static void SetColor(Material m, string p, Color v) { if (m.HasProperty(p)) m.SetColor(p, v); }
        static void SetFloat(Material m, string p, float v) { if (m.HasProperty(p)) m.SetFloat(p, v); }

        // â”€â”€ Autopilot task entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        public static bool RunAsTask(out string reason)
        {
            try { PaintAll(); reason = "IslandTree arborikÃ¼ltÃ¼r boyama tamam."; return true; }
            catch (System.Exception ex) { reason = $"IslandTreePainter hata: {ex.Message}"; return false; }
        }
    }
}
#endif

