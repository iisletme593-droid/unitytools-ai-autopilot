using UnityEngine;
using UnityEngine.Events;

namespace Gameplay
{
    /// Kale kapısı mini-boss karşılaşması (dikey dilim 1 finali).
    /// Oyuncu tetik alanına girince boss'u aktifler.
    public class BossEncounterManager : MonoBehaviour
    {
        public EnemyAIController boss;
        public float triggerRadius = 10f;
        public UnityEvent onEncounterStart;
        public UnityEvent onBossDefeated;

        bool _started;

        void Update()
        {
            if (_started || boss == null) return;
            var player = GameObject.FindGameObjectWithTag("Player");
            if (player == null) return;
            if (Vector3.Distance(player.transform.position, transform.position) <= triggerRadius)
            {
                _started = true;
                boss.aggroRange = Mathf.Max(boss.aggroRange, triggerRadius * 2f);
                onEncounterStart?.Invoke();
                if (boss.Combat != null) boss.Combat.OnDied += () => onBossDefeated?.Invoke();
            }
        }
    }
}
