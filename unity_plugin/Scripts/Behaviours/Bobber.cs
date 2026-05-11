// Runtime: bobs this GameObject sinusoidally along a local axis.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Bobber")]
    public class Bobber : MonoBehaviour
    {
        [Tooltip("Direction to bob along. World-space.")]
        public Vector3 axis = Vector3.up;

        [Tooltip("Peak amplitude in world units (full swing is 2x this).")]
        public float amplitude = 0.5f;

        [Tooltip("Period of one full oscillation in seconds.")]
        public float periodSec = 2f;

        [Tooltip("Random phase offset so multiple bobbers don't sync.")]
        public bool randomPhase = true;

        Vector3 _origin;
        float _phase;

        void Awake()
        {
            _origin = transform.position;
            _phase = randomPhase ? Random.value * Mathf.PI * 2f : 0f;
            if (axis == Vector3.zero) axis = Vector3.up;
        }

        void Update()
        {
            float omega = (periodSec > 0.0001f) ? (Mathf.PI * 2f / periodSec) : 0f;
            float y = Mathf.Sin(Time.time * omega + _phase) * amplitude;
            transform.position = _origin + axis.normalized * y;
        }
    }
}
