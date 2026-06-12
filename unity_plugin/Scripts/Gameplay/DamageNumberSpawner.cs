using UnityEngine;

namespace Gameplay
{
    /// Hasar sayısı gösterimi; şimdilik konsol + sahne izi, cilada world-space UI.
    public class DamageNumberSpawner : MonoBehaviour
    {
        public void Spawn(Vector3 worldPos, float amount, bool critical = false)
        {
            Debug.DrawRay(worldPos, Vector3.up, critical ? Color.red : Color.white, 0.5f);
        }
    }
}
