using UnityEngine;

namespace Gameplay
{
    /// Built-in pipeline atmosfer ayarları (HDRP'ye geçince Volume'a evrilir).
    /// Kamera ve render ayarlarını Thorny Ivy gotik görünümüne çeker.
    public class PostProcessSetup : MonoBehaviour
    {
        public Color cameraBackground = new Color(0.05f, 0.06f, 0.09f);

        void Start()
        {
            var cam = Camera.main;
            if (cam != null)
            {
                cam.clearFlags = RenderSettings.skybox != null ? CameraClearFlags.Skybox : CameraClearFlags.SolidColor;
                cam.backgroundColor = cameraBackground;
                cam.allowHDR = true;
            }
            QualitySettings.shadows = ShadowQuality.All;
        }
    }
}
