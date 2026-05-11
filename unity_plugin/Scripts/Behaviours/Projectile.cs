// Runtime: a self-propelled object that flies in its forward direction,
// auto-destroys after a lifetime or on collision, and damages anything
// hit that has an Enemy component. Hooks both 3D + 2D physics.
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Projectile")]
    public class Projectile : MonoBehaviour
    {
        [Tooltip("World units per second along this transform's forward axis.")]
        public float speed = 12f;

        [Tooltip("Auto-destroy after this many seconds (failsafe so off-screen projectiles don't leak).")]
        public float lifetime = 4f;

        [Tooltip("Damage dealt to any Enemy hit. Use 1 for one-shot kills.")]
        public int damage = 1;

        [Tooltip("Tag / name of objects to ignore (usually the shooter itself).")]
        public string ignoreNamePrefix = "Player";

        void Start()
        {
            if (lifetime > 0f) Destroy(gameObject, lifetime);
        }

        void Update()
        {
            transform.position += transform.forward * speed * Time.deltaTime;
        }

        void OnTriggerEnter(Collider other)
        {
            HandleHit(other.gameObject);
        }

        void OnTriggerEnter2D(Collider2D other)
        {
            HandleHit(other.gameObject);
        }

        void HandleHit(GameObject other)
        {
            if (other == null) return;
            if (!string.IsNullOrEmpty(ignoreNamePrefix) &&
                other.name.StartsWith(ignoreNamePrefix))
            {
                return;   // shooter or friendly
            }
            var enemy = other.GetComponent<Enemy>();
            if (enemy != null) enemy.TakeDamage(damage);
            Destroy(gameObject);
        }
    }
}
