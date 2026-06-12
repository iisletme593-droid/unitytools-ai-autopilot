// THORNY_HDRP: HDRP paketi projeye eklenince Project Settings > Player >
// Scripting Define Symbols'a THORNY_HDRP yazilarak bu dosya devreye alinir.
// Built-in pipeline projede HDRP tipleri derlenemez; o yuzden kapali tutulur.
#if UNITY_EDITOR && THORNY_HDRP
using System.IO;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEditor.Rendering.HighDefinition;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace Autopilot
{
    // Runs once after HDRP package is imported.
    // Converts all Standard materials, creates HDRP pipeline asset + global settings.
    [InitializeOnLoad]
    public static class HdrpMigrationSetup
    {
        private const string DoneKey = "ThornyIvy_HdrpMigrationDone_v2";

        static HdrpMigrationSetup()
        {
            if (!AutopilotExecutionMode.ShouldRunAutomatic("HdrpMigrationSetup")) return;
            if (SessionState.GetBool(DoneKey, false)) return;
            if (!IsHdrpAvailable()) return;
            EditorApplication.delayCall += RunMigration;
        }

        private static bool IsHdrpAvailable()
        {
            return System.Type.GetType(
                "UnityEngine.Rendering.HighDefinition.HDRenderPipelineAsset," +
                "Unity.RenderPipelines.HighDefinition.Runtime") != null;
        }

        private static void RunMigration()
        {
            SessionState.SetBool(DoneKey, true);
            Debug.Log("[HdrpMigrationSetup] Starting HDRP migration...");

            EnsureHdrpPipelineAsset();
            EnsureHdrpVolume();
            MigrateStandardMaterials();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[HdrpMigrationSetup] Migration complete.");
        }

        private static void EnsureHdrpPipelineAsset()
        {
            const string assetPath = "Assets/Settings/HDRPAsset.asset";
            Directory.CreateDirectory(
                Path.Combine(Application.dataPath, "Settings"));

            var existing = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(assetPath);
            if (existing != null)
            {
                GraphicsSettings.defaultRenderPipeline = existing;
                QualitySettings.renderPipeline = existing;
                return;
            }

            var asset = ScriptableObject.CreateInstance<HDRenderPipelineAsset>();
            // 4K, anti-aliasing, ray tracing disabled for performance
            if (asset is HDRenderPipelineAsset hdrp)
            {
                var s = hdrp.currentPlatformRenderPipelineSettings;
                s.supportRayTracing = false;
                s.colorBufferFormat = RenderPipelineSettings.ColorBufferFormat.R16G16B16A16;
                hdrp.currentPlatformRenderPipelineSettings = s;
            }
            AssetDatabase.CreateAsset(asset, assetPath);
            GraphicsSettings.defaultRenderPipeline = asset;
            QualitySettings.renderPipeline = asset;
            Debug.Log($"[HdrpMigrationSetup] Created HDRP Asset: {assetPath}");
        }

        private static void EnsureHdrpVolume()
        {
            const string profilePath = "Assets/Settings/HDRPDefaultProfile.asset";
            var profileAsset = AssetDatabase.LoadAssetAtPath<VolumeProfile>(profilePath);
            if (profileAsset == null)
            {
                profileAsset = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profileAsset, profilePath);

                var exposure = profileAsset.Add<Exposure>(true);
                exposure.mode.Override(ExposureMode.Fixed);
                exposure.fixedExposure.Override(1.2f);

                var bloom = profileAsset.Add<Bloom>(true);
                bloom.threshold.Override(0.9f);
                bloom.intensity.Override(0.8f);
                bloom.scatter.Override(0.65f);

                var vignette = profileAsset.Add<Vignette>(true);
                vignette.intensity.Override(0.3f);
                vignette.smoothness.Override(0.4f);

                var fog = profileAsset.Add<Fog>(true);
                fog.enabled.Override(true);
                fog.baseHeight.Override(0f);
                fog.maximumHeight.Override(180f);
                fog.meanFreePath.Override(70f);
                fog.albedo.Override(new Color(0.62f, 0.64f, 0.68f));

                var shadows = profileAsset.Add<HDShadowSettings>(true);
                shadows.maxShadowDistance.Override(150f);

                var colorAdj = profileAsset.Add<ColorAdjustments>(true);
                colorAdj.postExposure.Override(0f);
                colorAdj.contrast.Override(15f);
                colorAdj.saturation.Override(-10f);

                AssetDatabase.SaveAssets();
            }

            // Apply to scene volume if one exists, else mark as default
            var vol = Object.FindAnyObjectByType<Volume>();
            if (vol != null && vol.isGlobal)
                vol.sharedProfile = profileAsset;
        }

        private static void MigrateStandardMaterials()
        {
            var guids = AssetDatabase.FindAssets("t:Material", new[] { "Assets" });
            int converted = 0;
            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var mat  = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) continue;
                var sn = mat.shader?.name ?? "";
                if (sn.StartsWith("Standard") || sn == "Legacy Shaders/Diffuse")
                {
                    mat.shader = Shader.Find("HDRP/Lit");
                    EditorUtility.SetDirty(mat);
                    converted++;
                }
            }
            if (converted > 0)
                Debug.Log($"[HdrpMigrationSetup] Converted {converted} materials to HDRP/Lit");
        }
    }
}
#endif
