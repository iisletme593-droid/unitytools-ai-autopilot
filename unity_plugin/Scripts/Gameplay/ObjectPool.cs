using System.Collections.Generic;
using UnityEngine;

namespace Gameplay
{
    /// Basit prefab havuzu (VFX/hasar yazıları için).
    public class ObjectPool : MonoBehaviour
    {
        public GameObject prefab;
        public int prewarmCount = 8;

        readonly Queue<GameObject> _pool = new Queue<GameObject>();

        void Start()
        {
            for (int i = 0; i < prewarmCount && prefab != null; i++)
            {
                var go = Instantiate(prefab, transform);
                go.SetActive(false);
                _pool.Enqueue(go);
            }
        }

        public GameObject Get(Vector3 position)
        {
            GameObject go = _pool.Count > 0 ? _pool.Dequeue() : (prefab != null ? Instantiate(prefab, transform) : null);
            if (go == null) return null;
            go.transform.position = position;
            go.SetActive(true);
            return go;
        }

        public void Return(GameObject go)
        {
            if (go == null) return;
            go.SetActive(false);
            _pool.Enqueue(go);
        }
    }
}
