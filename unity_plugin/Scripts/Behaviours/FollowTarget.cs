// Runtime: smoothly tracks a named GameObject. Caches the target on first
// successful lookup so we don't pay GameObject.Find every frame.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/FollowTarget")]
    public class FollowTarget : MonoBehaviour
    {
        [Tooltip("Name of the target GameObject (looked up via GameObject.Find).")]
        public string targetName = "Player";

        [Tooltip("World-space offset added to the target position before tracking.")]
        public Vector3 offset = new Vector3(0f, 2f, -5f);

        [Tooltip("Higher = snappier follow. 0 = locked, 10 = near-instant.")]
        public float smoothing = 5f;

        [Tooltip("If true, also rotate to LookAt the target.")]
        public bool lookAtTarget = false;

        Transform _cachedTarget;

        void Update()
        {
            if (_cachedTarget == null)
            {
                if (string.IsNullOrEmpty(targetName)) return;
                var go = GameObject.Find(targetName);
                if (go == null) return;
                _cachedTarget = go.transform;
            }
            Vector3 desired = _cachedTarget.position + offset;
            if (smoothing <= 0f)
            {
                transform.position = desired;
            }
            else
            {
                transform.position = Vector3.Lerp(
                    transform.position, desired, 1f - Mathf.Exp(-smoothing * Time.deltaTime));
            }
            if (lookAtTarget) transform.LookAt(_cachedTarget);
        }
    }
}
