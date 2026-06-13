using UnityEngine;

namespace Gameplay
{
    /// Sis yoğunluğunu hafifçe dalgalandırır (Thorny Ivy mavi-gri sisi).
    public class WeatherSystem : MonoBehaviour
    {
        public Color fogColor = new Color(0.45f, 0.53f, 0.62f);
        public float baseFogDensity = 0.022f;
        public float densityWobble = 0.006f;
        public float wobbleSpeed = 0.05f;

        void Start()
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = fogColor;
        }

        void Update()
        {
            float t = Mathf.PerlinNoise(Time.time * wobbleSpeed, 0.37f);
            RenderSettings.fogDensity = baseFogDensity + (t - 0.5f) * 2f * densityWobble;
        }
    }
}
