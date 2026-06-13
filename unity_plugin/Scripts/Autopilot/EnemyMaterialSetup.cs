#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Autopilot
{
    // Dark-fantasy enemy materials: Brute (crimson skin), Shadow (void purple), Beast (toxic green).
    // Auto-runs once per session after compile. Manual: Tools > Autopilot > Apply Enemy Materials
    [InitializeOnLoad]
    public static class EnemyMaterialSetup
    {
        private const string DoneKey = "ThornyIvy_EnemyMat_v2";
        private const string MatDir  = "Assets/Materials/Enemy";

        static EnemyMaterialSetup()
        {
            if (!AutopilotExecutionMode.ShouldRunAutomatic("EnemyMaterialSetup")) return;
            if (SessionState.GetBool(DoneKey, false)) return;
            EditorApplication.delayCall += AutoApply;
        }

        private static void AutoApply()
        {
            if (SessionState.GetBool(DoneKey, false)) return;
            SessionState.SetBool(DoneKey, true);
            Apply();
        }

        [MenuItem("Tools/Autopilot/Apply Enemy Materials")]
        public static void Apply()
        {
            EnsureDir(MatDir);

            var brute  = GetOrCreateMaterial("M_Enemy_Brute",
                new Color(0.09f, 0.05f, 0.04f),   // çok koyu kahve deri
                metallic: 0.04f, smoothness: 0.18f,
                emissive: new Color(2.5f, 0.08f, 0.02f));   // kızıl parıltı

            var shadow = GetOrCreateMaterial("M_Enemy_Shadow",
                new Color(0.04f, 0.03f, 0.10f),   // koyu indigo
                metallic: 0.12f, smoothness: 0.55f,
                emissive: new Color(0.4f, 0.1f, 2.8f));     // mor hayalet aura

            var beast  = GetOrCreateMaterial("M_Enemy_Beast",
                new Color(0.08f, 0.11f, 0.06f),   // gri-yeşil organik
                metallic: 0.01f, smoothness: 0.12f,
                emissive: new Color(0.1f, 1.8f, 0.05f));    // zehir yeşili

            AssignToEnemies(brute, shadow, beast);
            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            Debug.Log("[EnemyMaterialSetup] Dark-fantasy malzemeler uygulandı.");
        }

        // ── Material factory ──────────────────────────────────────────────────
        private static Material GetOrCreateMaterial(string name, Color baseColor,
            float metallic, float smoothness, Color emissive)
        {
            string path = $"{MatDir}/{name}.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing != null) return existing;

            var mat = new Material(BestShader());
            SetBaseColor(mat, baseColor);
            SetMetallicSmoothness(mat, metallic, smoothness);
            SetEmissive(mat, emissive);

            AssetDatabase.CreateAsset(mat, path);
            return mat;
        }

        private static Shader BestShader() =>
            Shader.Find("HDRP/Lit")
            ?? Shader.Find("Universal Render Pipeline/Lit")
            ?? Shader.Find("Standard");

        private static void SetBaseColor(Material m, Color c)
        {
            if (m.HasProperty("_BaseColor"))  m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color"))      m.SetColor("_Color", c);
        }

        private static void SetMetallicSmoothness(Material m, float metallic, float smoothness)
        {
            if (m.HasProperty("_Metallic"))   m.SetFloat("_Metallic",   metallic);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smoothness);
            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", smoothness);
        }

        private static void SetEmissive(Material m, Color hdrColor)
        {
            m.EnableKeyword("_EMISSION");
            if (m.HasProperty("_EmissiveColor"))
            {
                // HDRP: store HDR value directly, disable separate intensity
                m.SetColor("_EmissiveColor", hdrColor);
                if (m.HasProperty("_EmissiveIntensity"))
                    m.SetFloat("_EmissiveIntensity", 1f);
                if (m.HasProperty("_UseEmissiveIntensity"))
                    m.SetFloat("_UseEmissiveIntensity", 0f);
            }
            else if (m.HasProperty("_EmissionColor"))
            {
                // Built-in / URP
                m.SetColor("_EmissionColor", hdrColor);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
            }
        }

        // ── Round-robin assignment to enemies ─────────────────────────────────
        private static void AssignToEnemies(Material brute, Material shadow, Material beast)
        {
            var enemies = UnityEngine.Object.FindObjectsByType<Gameplay.EnemyAIController>(
                FindObjectsInactive.Include);
            int i = 0;
            foreach (var e in enemies)
            {
                Material mat = (i % 3) switch { 0 => brute, 1 => shadow, _ => beast };
                ApplyToRenderers(e.transform, mat);
                i++;
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"[EnemyMaterialSetup] {i} düşmana malzeme atandı.");
        }

        private static void ApplyToRenderers(Transform root, Material mat)
        {
            foreach (var r in root.GetComponentsInChildren<Renderer>())
            {
                if (r is ParticleSystemRenderer) continue;
                var mats = new Material[r.sharedMaterials.Length];
                for (int j = 0; j < mats.Length; j++) mats[j] = mat;
                r.sharedMaterials = mats;
                EditorUtility.SetDirty(r);
            }
        }

        // ── Folder helper ─────────────────────────────────────────────────────
        private static void EnsureDir(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = System.IO.Path.GetDirectoryName(path).Replace('\\', '/');
            string folder = System.IO.Path.GetFileName(path);
            EnsureDir(parent);
            AssetDatabase.CreateFolder(parent, folder);
        }
    }
}
#endif

