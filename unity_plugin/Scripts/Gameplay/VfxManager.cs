using UnityEngine;

namespace Gameplay
{
    /// Vuruş/parıltı efektleri için merkezi kanca; şimdilik kayıt noktası.
    public class VfxManager : MonoBehaviour
    {
        public static VfxManager Instance { get; private set; }
        void Awake() { Instance = this; }

        public void PlayHitSpark(Vector3 position)
        {
            // Dilim 1 cilası: particle prefab. Şimdilik debug iz.
            Debug.DrawRay(position, Vector3.up * 0.6f, Color.yellow, 0.4f);
        }
    }
}
