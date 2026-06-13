using UnityEngine;

namespace Gameplay
{
    /// Düşman ölünce eşya/XP bırakma tanımı.
    public class LootDrop : MonoBehaviour
    {
        public string itemId = "gold";
        public int minCount = 1;
        public int maxCount = 3;
        public float xpReward = 12f;

        CombatComponent _combat;

        void Awake()
        {
            _combat = GetComponent<CombatComponent>();
            if (_combat != null) _combat.OnDied += GiveRewards;
        }

        void GiveRewards()
        {
            var player = GameObject.FindGameObjectWithTag("Player");
            if (player == null) return;
            var inv = player.GetComponent<InventoryComponent>();
            if (inv != null) inv.Add(itemId, Random.Range(minCount, maxCount + 1));
            var xp = player.GetComponent<ExperienceComponent>();
            if (xp != null) xp.AddXp(xpReward);
        }
    }
}
