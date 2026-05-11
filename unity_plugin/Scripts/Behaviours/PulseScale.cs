// Runtime: pulses this GameObject's scale sinusoidally between min and max.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/PulseScale")]
    public class PulseScale : MonoBehaviour
    {
        [Tooltip("Smallest uniform scale factor.")]
        public float minScale = 0.9f;

        [Tooltip("Largest uniform scale factor.")]
        public float maxScale = 1.1f;

        [Tooltip("Period of one full pulse cycle in seconds.")]
        public float periodSec = 1.2f;

        Vector3 _baseScale;

        void Awake()
        {
            _baseScale = transform.localScale;
            if (_baseScale == Vector3.zero) _baseScale = Vector3.one;
        }

        void Update()
        {
            float omega = (periodSec > 0.0001f) ? (Mathf.PI * 2f / periodSec) : 0f;
            float t = (Mathf.Sin(Time.time * omega) + 1f) * 0.5f;   // 0..1
            float f = Mathf.Lerp(minScale, maxScale, t);
            transform.localScale = _baseScale * f;
        }
    }
}
