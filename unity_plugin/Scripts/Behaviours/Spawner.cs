// Runtime: clones a named template GameObject at fixed intervals,
// capped by maxAlive. Spawns within spawnRadius of this transform.
// Designed for wave-survival / endless-runner genres: place a hidden
// enemy template, point the Spawner at it, set interval + cap.
using System.Collections.Generic;
using UnityEngine;

namespace UnityTools.Behaviours
{
    [AddComponentMenu("UnityTools/Behaviours/Spawner")]
    public class Spawner : MonoBehaviour
    {
        [Tooltip("Name of a GameObject in the scene to clone. Hidden / inactive recommended.")]
        public string templateName = "EnemyTemplate";

        [Tooltip("Seconds between spawn attempts.")]
        public float interval = 2f;

        [Tooltip("Maximum live clones at once. New spawns wait until one dies.")]
        public int maxAlive = 5;

        [Tooltip("Random world-space offset radius from this transform.")]
        public float spawnRadius = 4f;

        [Tooltip("Delay before the first spawn (seconds).")]
        public float warmup = 1f;

        [Tooltip("If true, spawn on a flat 2D plane (xz). If false, full 3D sphere.")]
        public bool flatXZ = true;

        GameObject _template;
        float _nextSpawnTime;
        readonly List<GameObject> _alive = new();

        void Start()
        {
            ResolveTemplate();
            _nextSpawnTime = Time.time + Mathf.Max(0f, warmup);
        }

        void ResolveTemplate()
        {
            if (_template != null) return;
            if (string.IsNullOrEmpty(templateName)) return;
            _template = GameObject.Find(templateName);
            if (_template == null)
            {
                Debug.LogWarning($"Spawner: template '{templateName}' not found; disabling.", this);
                enabled = false;
                return;
            }
            _template.SetActive(false);
        }

        void Update()
        {
            if (_template == null) return;
            // Prune dead refs
            for (int i = _alive.Count - 1; i >= 0; i--)
            {
                if (_alive[i] == null) _alive.RemoveAt(i);
            }
            if (_alive.Count >= maxAlive) return;
            if (Time.time < _nextSpawnTime) return;

            Vector3 offset;
            if (flatXZ)
            {
                Vector2 c = Random.insideUnitCircle * spawnRadius;
                offset = new Vector3(c.x, 0f, c.y);
            }
            else
            {
                offset = Random.insideUnitSphere * spawnRadius;
            }
            Vector3 pos = transform.position + offset;
            var clone = Object.Instantiate(_template, pos, Quaternion.identity);
            clone.SetActive(true);
            clone.name = $"{_template.name}_spawn{_alive.Count}";
            _alive.Add(clone);
            _nextSpawnTime = Time.time + Mathf.Max(0.1f, interval);
        }
    }
}
