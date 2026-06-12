using UnityEngine;

namespace Gameplay
{
    /// Kamp ateşi: titreyen ışık + checkpoint (GAME_DESIGN kararı 3:
    /// oyuncu ölünce son dokunduğu kamp ateşinden doğar).
    public class CampfireVfx : MonoBehaviour
    {
        public float baseIntensity = 2.4f;
        public float flicker = 0.6f;
        public float flickerSpeed = 9f;
        public Color fireColor = new Color(1f, 0.55f, 0.18f);
        public float checkpointRadius = 3.5f;

        public static Vector3? LastCheckpoint { get; private set; }

        Light _light;

        void Awake()
        {
            _light = GetComponentInChildren<Light>();
            if (_light == null)
            {
                var lightGo = new GameObject("CampfireLight");
                lightGo.transform.SetParent(transform, false);
                lightGo.transform.localPosition = Vector3.up * 0.8f;
                _light = lightGo.AddComponent<Light>();
                _light.type = LightType.Point;
                _light.range = 9f;
            }
            _light.color = fireColor;
        }

        void Update()
        {
            float n = Mathf.PerlinNoise(Time.time * flickerSpeed, 0.5f);
            _light.intensity = baseIntensity + (n - 0.5f) * 2f * flicker;

            var player = GameObject.FindGameObjectWithTag("Player");
            if (player != null &&
                Vector3.Distance(player.transform.position, transform.position) <= checkpointRadius)
            {
                LastCheckpoint = transform.position + Vector3.forward * 1.5f;
            }
        }
    }
}
