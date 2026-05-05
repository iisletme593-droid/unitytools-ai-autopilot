#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace Autopilot
{
    // Referans gÃ¶rsele (dark fantasy orman, log cabin, sis atmosferi) gÃ¶re
    // sahne aydÄ±nlatmasÄ±nÄ±, sis ve ambient Ä±ÅŸÄ±ÄŸÄ±nÄ± otomatik ayarlar.
    // El ile: Tools > Autopilot > Apply Reference Aesthetics
    // NOT: [InitializeOnLoad] kaldÄ±rÄ±ldÄ± â€” her domain reload'da sahneye nesne ekliyordu.
    public static class SceneReferenceAesthetics
    {
        [MenuItem("Tools/Autopilot/Apply Reference Aesthetics")]
        public static void Apply()
        {
            ApplyLighting();
            ApplyFog();
            ApplySkybox();
            // SpawnMissingProps kaldÄ±rÄ±ldÄ± â€” kamp ateÅŸi artÄ±k SceneBuilder.BuildLighting() iÃ§inde
            EditorSceneManager.MarkAllScenesDirty();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            Debug.Log("[SceneAesthetics] Referans gÃ¶rsele gÃ¶re sahne gÃ¼ncellendi.");
        }

        // â”€â”€ AydÄ±nlatma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        private static void ApplyLighting()
        {
            // Ambient: koyu mavi-gri (dark fantasy geceleri)
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.04f, 0.05f, 0.08f);
            RenderSettings.ambientIntensity = 0.6f;

            // Directional light: soluk mavi-beyaz, hafif eÄŸimli (castle arkasÄ±ndan gÃ¼neÅŸ)
            var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include);
            Light sun = null;
            foreach (var l in lights)
                if (l.type == LightType.Directional) { sun = l; break; }

            if (sun == null)
            {
                var go = new GameObject("Directional_Sun");
                sun = go.AddComponent<Light>();
                sun.type = LightType.Directional;
            }

            sun.color = new Color(0.78f, 0.82f, 0.95f);  // soÄŸuk sabah Ä±ÅŸÄ±ÄŸÄ±
            sun.intensity = 0.7f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.85f;
            sun.transform.rotation = Quaternion.Euler(32f, -145f, 0f);
            Debug.Log("[SceneAesthetics] AydÄ±nlatma ayarlandÄ±.");
        }

        // â”€â”€ Sis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        private static void ApplyFog()
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            // Referans: yoÄŸun sis, soÄŸuk mavi-gri ton
            RenderSettings.fogColor = new Color(0.20f, 0.24f, 0.30f);
            RenderSettings.fogDensity = 0.025f;
            Debug.Log("[SceneAesthetics] Sis ayarlandÄ±.");
        }

        // â”€â”€ Skybox â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        private static void ApplySkybox()
        {
            // HDR panoramic skybox
            const string hdrPath = "Assets/Art/Environment/HDRI/abandoned_pathway_4k.hdr";
            var hdrTex = AssetDatabase.LoadAssetAtPath<Cubemap>(hdrPath);
            Texture2D hdrTex2D = null;
            if (hdrTex == null)
                hdrTex2D = AssetDatabase.LoadAssetAtPath<Texture2D>(hdrPath);

            if (hdrTex != null || hdrTex2D != null)
            {
                Material skyMat = new Material(Shader.Find("Skybox/Cubemap"));
                if (skyMat.shader == null || skyMat.shader.name == "Hidden/InternalErrorShader")
                    skyMat = new Material(Shader.Find("Skybox/Panoramic"));

                if (hdrTex2D != null)
                    skyMat.SetTexture("_MainTex", hdrTex2D);
                else
                    skyMat.SetTexture("_Tex", hdrTex);

                skyMat.SetFloat("_Exposure", 0.4f);  // koyu tutmak iÃ§in dÃ¼ÅŸÃ¼k exposure

                const string matPath = "Assets/Art/Environment/HDRI/DarkForestSky.mat";
                AssetDatabase.CreateAsset(skyMat, matPath);
                AssetDatabase.SaveAssets();

                RenderSettings.skybox = skyMat;
                DynamicGI.UpdateEnvironment();
                Debug.Log("[SceneAesthetics] Skybox uygulandÄ±: abandoned_pathway HDRI");
            }
            else
            {
                // HDR henÃ¼z import edilmedi â€” koyu gradient skybox fallback
                Material skyMat = new Material(Shader.Find("Skybox/Procedural"));
                if (skyMat != null && skyMat.shader != null)
                {
                    skyMat.SetFloat("_SunSize", 0.02f);
                    skyMat.SetFloat("_Exposure", 0.3f);
                    skyMat.SetColor("_SkyTint", new Color(0.08f, 0.10f, 0.15f));
                    skyMat.SetColor("_GroundColor", new Color(0.12f, 0.10f, 0.08f));
                    RenderSettings.skybox = skyMat;
                }
                Debug.Log("[SceneAesthetics] HDR bulunamadÄ±, procedural skybox uygulandÄ±.");
            }
        }

    }
}
#endif

