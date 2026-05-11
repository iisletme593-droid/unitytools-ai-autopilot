// Runtime: instantiates a projectile template on fire input. Rate-
// limited via fireRate. Aims at the mouse-screen ray hit point (3D)
// or straight forward (if aimAtMouse is false). Template should be a
// GameObject in the scene with a Projectile component and be inactive
// (Shooter clones it via Instantiate and activates the clone).
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Shooter")]
    public class Shooter : MonoBehaviour
    {
        [Tooltip("Name of a GameObject in the scene to clone. Should have a Projectile component.")]
        public string projectileTemplateName = "ProjectileTemplate";

        [Tooltip("Input key. Default Mouse0 (left click). Use KeyCode.Space for keyboard.")]
        public KeyCode fireKey = KeyCode.Mouse0;

        [Tooltip("Max shots per second. 0 disables rate limiting.")]
        public float fireRate = 4f;

        [Tooltip("If true, aim toward the mouse cursor's world-space point (3D ground plane).")]
        public bool aimAtMouse = true;

        [Tooltip("Vertical offset for spawned projectile (above the shooter feet).")]
        public float spawnHeightOffset = 1.0f;

        GameObject _template;
        float _nextFireTime;

        void Start()
        {
            ResolveTemplate();
        }

        void ResolveTemplate()
        {
            if (_template != null) return;
            if (string.IsNullOrEmpty(projectileTemplateName)) return;
            var found = GameObject.Find(projectileTemplateName);
            if (found == null)
            {
                Debug.LogWarning($"Shooter: projectile template '{projectileTemplateName}' not found in scene; fire is disabled.", this);
                return;
            }
            _template = found;
            // Hide the template so it doesn't render in the scene
            _template.SetActive(false);
        }

        void Update()
        {
            if (Input.GetKey(fireKey) && Time.time >= _nextFireTime)
            {
                Fire();
                _nextFireTime = Time.time + (fireRate > 0f ? 1f / fireRate : 0f);
            }
        }

        public void Fire()
        {
            if (_template == null) { ResolveTemplate(); if (_template == null) return; }
            Vector3 origin = transform.position + Vector3.up * spawnHeightOffset;
            Quaternion rotation = transform.rotation;

            if (aimAtMouse && Camera.main != null)
            {
                Plane ground = new Plane(Vector3.up, new Vector3(0f, origin.y, 0f));
                Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
                if (ground.Raycast(ray, out float enter))
                {
                    Vector3 target = ray.GetPoint(enter);
                    Vector3 toTarget = target - origin;
                    toTarget.y = 0f;
                    if (toTarget.sqrMagnitude > 0.0001f)
                    {
                        rotation = Quaternion.LookRotation(toTarget.normalized, Vector3.up);
                    }
                }
            }

            var clone = Object.Instantiate(_template, origin, rotation);
            clone.SetActive(true);
            // Name the clone uniquely so Spawner caps still work if a Spawner
            // is also tracking these.
            clone.name = $"{_template.name}_shot";
        }
    }
}
