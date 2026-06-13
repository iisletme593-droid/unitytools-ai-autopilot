using UnityEngine;

namespace Gameplay
{
    /// Skybox/ambient yönetimi; gece skybox'ı üretilince buradan atanır.
    public class SkyboxManager : MonoBehaviour
    {
        public Material nightSkybox;
        public Color ambientColor = new Color(0.12f, 0.14f, 0.2f);

        void Start()
        {
            if (nightSkybox != null) RenderSettings.skybox = nightSkybox;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = ambientColor;
        }
    }
}
