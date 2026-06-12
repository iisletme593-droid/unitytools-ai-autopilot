using System;
using UnityEngine;

namespace Gameplay
{
    /// Level/XP iskeleti (Knight Online level ruhu; eğri sonra ayarlanır).
    public class ExperienceComponent : MonoBehaviour
    {
        public int level = 1;
        public float currentXp;
        public float xpToNext = 100f;
        public float xpCurveMultiplier = 1.35f;

        public event Action<int> OnLevelUp;

        public void AddXp(float amount)
        {
            if (amount <= 0f) return;
            currentXp += amount;
            while (currentXp >= xpToNext)
            {
                currentXp -= xpToNext;
                level++;
                xpToNext *= xpCurveMultiplier;
                OnLevelUp?.Invoke(level);
            }
        }
    }
}
