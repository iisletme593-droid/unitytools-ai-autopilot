using UnityEngine;

namespace Gameplay
{
    /// Hedef kilitleme: Tab ile en yakın düşmana kilitlenir/bırakır.
    public class LockOnSystem : MonoBehaviour
    {
        public float lockRange = 14f;
        public EnemyAIController CurrentTarget { get; private set; }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Tab))
            {
                if (CurrentTarget != null) { CurrentTarget = null; return; }
                CurrentTarget = FindNearestEnemy();
            }
            if (CurrentTarget != null)
            {
                bool gone = CurrentTarget == null || CurrentTarget.Combat == null || CurrentTarget.Combat.IsDead;
                if (gone || Vector3.Distance(transform.position, CurrentTarget.transform.position) > lockRange * 1.4f)
                    CurrentTarget = null;
            }
        }

        EnemyAIController FindNearestEnemy()
        {
            EnemyAIController best = null;
            float bestDist = lockRange;
            foreach (var e in Object.FindObjectsByType<EnemyAIController>(FindObjectsSortMode.None))
            {
                if (e.Combat != null && e.Combat.IsDead) continue;
                float d = Vector3.Distance(transform.position, e.transform.position);
                if (d < bestDist) { bestDist = d; best = e; }
            }
            return best;
        }
    }
}
