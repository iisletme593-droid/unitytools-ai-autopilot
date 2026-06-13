// Editor-only araç: player build'de derlenmemeli, yoksa build kırılır.
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Autopilot
{
    // Reads generated_assets_manifest.json produced by hf_asset_generator.py
    // and imports / applies the generated textures into the current scene.
    // Run via: Tools > Autopilot > Load Generated Assets
    public static class GeneratedAssetLoader
    {
        private const string ManifestRelPath = "output/unity/generated_assets_manifest.json";

        [MenuItem("Tools/Autopilot/Load Generated Assets")]
        public static void LoadGeneratedAssets()
        {
            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
            string manifestPath = Path.Combine(repoRoot, ManifestRelPath).Replace('\\', '/');

            if (!File.Exists(manifestPath))
            {
                Debug.LogWarning($"[GeneratedAssetLoader] Manifest not found: {manifestPath}");
                return;
            }

            var manifest = JsonUtility.FromJson<AssetsManifest>(File.ReadAllText(manifestPath));
            if (manifest?.assets_list == null || manifest.assets_list.Count == 0)
            {
                Debug.LogWarning("[GeneratedAssetLoader] No assets in manifest.");
                return;
            }

            int imported = 0;
            foreach (var entry in manifest.assets_list)
            {
                if (entry == null || string.IsNullOrEmpty(entry.path)) continue;
                if (entry.status == "failed") continue;

                string absPath = Path.Combine(repoRoot, entry.path).Replace('\\', '/');
                if (!File.Exists(absPath))
                {
                    Debug.LogWarning($"[GeneratedAssetLoader] Asset file not found: {absPath}");
                    continue;
                }

                // Copy into Assets folder so Unity can import it
                string destRelative = $"Assets/GeneratedAssets/{entry.subfolder}/{entry.filename}";
                string destAbs = Path.Combine(Application.dataPath,
                    $"GeneratedAssets/{entry.subfolder}/{entry.filename}").Replace('\\', '/');

                Directory.CreateDirectory(Path.GetDirectoryName(destAbs)!);
                File.Copy(absPath, destAbs, overwrite: true);
                AssetDatabase.ImportAsset(destRelative, ImportAssetOptions.ForceUpdate);

                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(destRelative);
                if (tex == null)
                {
                    Debug.LogWarning($"[GeneratedAssetLoader] Could not load texture: {destRelative}");
                    continue;
                }

                ApplyTextureToScene(entry.id, tex);
                imported++;
                Debug.Log($"[GeneratedAssetLoader] Imported {entry.id} → {destRelative} (score:{entry.score:F3})");
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[GeneratedAssetLoader] Done — {imported} asset(s) imported.");
        }

        private static void ApplyTextureToScene(string assetId, Texture2D tex)
        {
            // Skybox special-case
            if (assetId == "skybox_night")
            {
                if (RenderSettings.skybox != null)
                {
                    RenderSettings.skybox.SetTexture("_MainTex", tex);
                    DynamicGI.UpdateEnvironment();
                }
                return;
            }

            // Find GameObject by name pattern, apply texture to its first renderer material
            string namePattern = AssetIdToObjectName(assetId);
            if (string.IsNullOrEmpty(namePattern)) return;

            var allRenderers = Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude);
            foreach (var rend in allRenderers)
            {
                if (!rend.gameObject.name.ToLowerInvariant().Contains(namePattern)) continue;
                var mat = rend.sharedMaterial;
                if (mat == null)
                {
                    mat = new Material(Shader.Find("Standard"));
                    rend.sharedMaterial = mat;
                }
                mat.mainTexture = tex;
                return;
            }
        }

        private static string AssetIdToObjectName(string assetId)
        {
            return assetId switch
            {
                "texture_forest_ground" => "terrain",
                "texture_tree_bark"     => "tree",
                "character_warrior"     => "player",
                "character_enemy_brute" => "enemy",
                "scene_campfire"        => "campfire",
                _                       => string.Empty,
            };
        }

        // ── JSON data model ────────────────────────────────────────────────────

        [System.Serializable]
        private class AssetsManifest
        {
            // Python saves a parallel assets_list (array) alongside the assets dict
            // because Unity's JsonUtility cannot deserialize JSON objects as dictionaries.
            public List<AssetEntry> assets_list;
            public string last_run;
            public int total_generated;
        }

        [System.Serializable]
        private class AssetEntry
        {
            public string id;
            public string path;
            public string subfolder;
            public string filename;
            public float score;
            public string status;
            public string generated_at;
        }
    }
}

#endif
