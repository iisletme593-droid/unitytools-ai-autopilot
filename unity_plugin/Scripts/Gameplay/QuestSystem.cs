using System.Collections.Generic;
using UnityEngine;

namespace Gameplay
{
    /// Görev iskeleti: id -> tamamlandı durumu (dilim 2'de genişler).
    public class QuestSystem : MonoBehaviour
    {
        readonly Dictionary<string, bool> _quests = new Dictionary<string, bool>();

        public void StartQuest(string id) { if (!_quests.ContainsKey(id)) _quests[id] = false; }
        public void CompleteQuest(string id) { _quests[id] = true; }
        public bool IsCompleted(string id) => _quests.TryGetValue(id, out bool done) && done;
    }
}
