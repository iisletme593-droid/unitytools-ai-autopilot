using UnityEngine;

namespace Gameplay
{
    /// Prosedürel dünya üretimi iskeleti (Valheim biome keşfi - dilim 2+).
    /// Şimdilik tohum ve alan tanımı taşır; üretim SceneBuilder/Autopilot'ta.
    public class ProceduralWorldGenerator : MonoBehaviour
    {
        public int seed = 41;
        public Vector2 worldSize = new Vector2(200f, 200f);
        public bool generated;
    }
}
