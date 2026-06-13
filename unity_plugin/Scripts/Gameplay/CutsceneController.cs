using UnityEngine;

namespace Gameplay
{
    /// Ara sahne iskeleti (kale girişi sineması vb. için yer tutucu).
    public class CutsceneController : MonoBehaviour
    {
        public bool IsPlaying { get; private set; }
        public void Play(string cutsceneId) { IsPlaying = true; }
        public void Stop() { IsPlaying = false; }
    }
}
