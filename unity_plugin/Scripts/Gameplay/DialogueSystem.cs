using UnityEngine;

namespace Gameplay
{
    /// Diyalog iskeleti (NPC'ler dilim 2+).
    public class DialogueSystem : MonoBehaviour
    {
        public bool IsDialogueActive { get; private set; }
        public void Begin(string speaker, string[] lines) { IsDialogueActive = true; }
        public void End() { IsDialogueActive = false; }
    }
}
