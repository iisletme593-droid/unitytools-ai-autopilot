// Runtime: moves this GameObject along a fixed world-space direction
// at constant speed. Designed for endless-runner genres where the
// world scrolls toward the player while the player stays in place.
// Attached to: ground tiles, obstacles (cloned by a Spawner), distant
// scenery.
//
// Optional auto-destroy past a Z threshold so the scroller leaks
// nothing as obstacles fly off-camera.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/AutoScroller")]
    public class AutoScroller : MonoBehaviour
    {
        [Tooltip("Direction to move along, world-space. Normalized on Awake.")]
        public Vector3 direction = new Vector3(0f, 0f, -1f);

        [Tooltip("World units per second.")]
        public float speed = 6f;

        [Tooltip("If true, destroys this GameObject when it crosses despawnAt along the direction axis (relative to origin).")]
        public bool despawnPastThreshold = true;

        [Tooltip("Despawn threshold along the direction axis. Default -20: an obstacle moving along -Z gets destroyed at z=-20.")]
        public float despawnAt = -20f;

        Vector3 _dirNormalized;

        void Awake()
        {
            _dirNormalized = direction.sqrMagnitude > 0.0001f
                ? direction.normalized
                : new Vector3(0f, 0f, -1f);
        }

        void Update()
        {
            transform.position += _dirNormalized * speed * Time.deltaTime;
            if (despawnPastThreshold)
            {
                float along = Vector3.Dot(transform.position, _dirNormalized);
                if (along < despawnAt)
                {
                    Destroy(gameObject);
                }
            }
        }
    }
}
