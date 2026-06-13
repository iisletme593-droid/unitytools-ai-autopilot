using UnityEngine;

namespace Gameplay
{
    /// Kameraya kısa sarsıntı (ağır vuruş/boss hissi).
    public class ScreenShake : MonoBehaviour
    {
        public float decay = 3.5f;
        float _trauma;
        Vector3 _baseLocalPos;

        void Awake() { _baseLocalPos = transform.localPosition; }

        public void AddTrauma(float amount) { _trauma = Mathf.Clamp01(_trauma + amount); }

        void LateUpdate()
        {
            if (_trauma <= 0f) { transform.localPosition = _baseLocalPos; return; }
            float shake = _trauma * _trauma;
            transform.localPosition = _baseLocalPos + new Vector3(
                (Mathf.PerlinNoise(Time.time * 25f, 0f) - 0.5f),
                (Mathf.PerlinNoise(0f, Time.time * 25f) - 0.5f), 0f) * 0.35f * shake;
            _trauma = Mathf.Max(0f, _trauma - decay * Time.deltaTime * _trauma);
        }
    }
}
