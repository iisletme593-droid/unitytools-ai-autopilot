// Runtime: spins this GameObject around a local axis at a constant speed.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Rotator")]
    public class Rotator : MonoBehaviour
    {
        [Tooltip("Local axis to rotate around. Normalised at start.")]
        public Vector3 axis = Vector3.up;

        [Tooltip("Rotation speed in degrees per second. Negative reverses direction.")]
        public float speedDegPerSec = 30f;

        void Awake()
        {
            if (axis == Vector3.zero) axis = Vector3.up;
            axis = axis.normalized;
        }

        void Update()
        {
            transform.Rotate(axis, speedDegPerSec * Time.deltaTime, Space.Self);
        }
    }
}
